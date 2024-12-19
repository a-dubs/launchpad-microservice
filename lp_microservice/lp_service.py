import enum
from itertools import islice
import random
import time
from typing import Literal, Optional, Union
import concurrent.futures
import requests
import json
import webbrowser

import os

import logging
from pprint import pformat, pprint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def log_pprint(obj, level=logging.INFO):
    if level == logging.DEBUG:
        logger.debug(pformat(obj))
    elif level == logging.INFO:
        logger.info(pformat(obj))
    elif level == logging.WARNING:
        logger.warning(pformat(obj))
    elif level == logging.ERROR:
        logger.error(pformat(obj))
    elif level == logging.CRITICAL:
        logger.critical(pformat(obj))
    else:
        logger.log(level, pformat(obj))


LP_CREDS = None

logger.info("Hello from lp_service.py")

##############################################################################
# Authentication ###############################
##############################################################################


def is_authenticated() -> bool:
    # check if a json file exists at LP_CREDS_PATH
    return os.path.exists(LP_CREDS_PATH)


LP_CREDS_PATH = "/var/opt/lp-microservice/launchpad_creds.json"


def wait_for_credentials(timeout=300, poll_interval=5):
    global LP_CREDS
    """
    Wait for the credentials file to be created.
    Poll every `poll_interval` seconds, and timeout after `timeout` seconds.
    """
    start_time = time.time()
    logger.info("Looking for credentials at %s", LP_CREDS_PATH)
    while not os.path.exists(LP_CREDS_PATH):
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout:
            logger.info("Error: Authentication not completed in time. Exiting.")
            return False
        logger.info("Waiting for credentials... Please complete authentication using the initialize command.")
        time.sleep(poll_interval)
    #  now read the credentials into LP_CREDS
    with open(LP_CREDS_PATH, "r") as f:
        LP_CREDS = json.load(f)
    logger.info("Credentials found. Starting the server.")
    return True


def _auth_step_1() -> tuple[str, str]:
    data = {"oauth_consumer_key": "launchpyd", "oauth_signature_method": "PLAINTEXT", "oauth_signature": "&"}
    r = requests.post("https://launchpad.net/+request-token", data=data)
    logger.debug(f"Auth Step 1 Response Status: {r.status_code}")
    logger.debug(f"Auth Step 1 Response Text: {r.text}")
    # Get oauth_token and oauth_token_secret from response
    oauth_token = r.text.split("&")[0].split("=")[1]
    oauth_token_secret = r.text.split("&")[1].split("=")[1]
    logger.debug(f"OAuth Token: {oauth_token}, OAuth Token Secret: {oauth_token_secret}")
    return oauth_token, oauth_token_secret


def _auth_step_2(oauth_token: str):
    # Redirect user to authorization URL
    auth_url = f"https://launchpad.net/+authorize-token?oauth_token={oauth_token}"
    logger.debug(f"Redirecting user to: {auth_url}")
    print("Opening browser for authentication. Please authorize the app.")
    webbrowser.open(auth_url)
    input("Press Enter after you have authorized the app.")


def _auth_step_3(oauth_token: str, oauth_token_secret: str):
    # Send a POST request to get the access token and secret
    data = {
        "oauth_consumer_key": "launchpyd",
        "oauth_signature_method": "PLAINTEXT",
        "oauth_signature": f"&{oauth_token_secret}",
        "oauth_token": oauth_token,
    }
    r = requests.post("https://launchpad.net/+access-token", data=data)
    logger.debug(f"Auth Step 3 Response Status: {r.status_code}")
    logger.debug(f"Auth Step 3 Response Text: {r.text}")
    # Get access_token and access_secret from response
    access_token = r.text.split("&")[0].split("=")[1]
    access_secret = r.text.split("&")[1].split("=")[1]
    # make directory if it doesn't exist
    os.makedirs(os.path.dirname(LP_CREDS_PATH), exist_ok=True)
    with open(LP_CREDS_PATH, "w") as f:
        json.dump({"access_token": access_token, "access_secret": access_secret}, f)
    logger.debug(f"Access token and secret saved to {LP_CREDS_PATH}")


def perform_authentication():
    global LP_CREDS
    try:
        with open(LP_CREDS_PATH, "r") as f:
            LP_CREDS = json.load(f)
            logger.info(f"Loaded LP credentials from {LP_CREDS_PATH}. No authentication setup needed.")
    except FileNotFoundError:
        logger.info(f"{LP_CREDS_PATH} does not exist. Starting authentication process.")
        oauth_token, oauth_token_secret = _auth_step_1()
        _auth_step_2(oauth_token=oauth_token)
        _auth_step_3(oauth_token=oauth_token, oauth_token_secret=oauth_token_secret)
        with open(LP_CREDS_PATH, "r") as f:
            LP_CREDS = json.load(f)


def _nonce():
    # Generate unsigned 64-bit random number
    return random.randint(0, 2**64 - 1)


##############################################################################
# API Requests ################################
##############################################################################


def _make_auth_header():
    oauth_token = LP_CREDS["access_token"]
    oauth_token_secret = LP_CREDS["access_secret"]
    headers = {
        "Authorization": f'OAuth realm="https://api.launchpad.net/", '
        f'oauth_consumer_key="launchpyd", '
        f'oauth_token="{oauth_token}", '
        f'oauth_signature_method="PLAINTEXT", '
        f'oauth_signature="&{oauth_token_secret}", '
        f"oauth_timestamp={time.time()}, "
        f'oauth_nonce="{_nonce()}", '
        f'oauth_version="1.0"'
    }
    return headers


def _convert_web_link_to_api_link(web_link):
    return web_link.replace("code.launchpad.net", "api.launchpad.net/devel")


def _lp_get(url: str, params: dict = {}, verbose: bool = False):
    if url:
        url = _convert_web_link_to_api_link(url)
    else:
        raise ValueError("URL cannot be None")
    headers = _make_auth_header()
    r = requests.get(url, headers=headers, params=params)
    logger.info(f"[GET] ({r.status_code}) {url} {[f'{k}={v}' for k, v in params.items()]}")
    if r.status_code >= 400:
        logger.error(f"[GET FAILED] {r.status_code} {r.reason} for {r.url} with params {params}")
        return None
    try:
        response_json = json.loads(r.text)
        if verbose:
            log_pprint(response_json)
        return response_json
    except json.JSONDecodeError:
        if verbose:
            logger.error(f"Failed to parse JSON response: {r.text}")
        return r


def _lp_post(url: str, params: dict = {}, data: dict = {}, verbose: bool = False):
    url = _convert_web_link_to_api_link(url)
    headers = _make_auth_header()
    r = requests.post(url, headers=headers, params=params, data=data)
    logger.info(f"[POST] ({r.status_code}) {url} {[f'{k}={v}' for k, v in params.items()]}")
    if verbose:
        log_pprint(data, level=logging.INFO)
    if r.status_code >= 400:
        logger.error(f"[POST FAILED] {r.status_code} {r.reason} for {r.url} with params {params} and data {data}")
        raise Exception(f"Failed to post data to {url} with params {params} and data {data}")
    return r


def _stringify_dict(d: dict):
    return "{" + ",".join([f'"{k}": "{v}"' for k, v in d.items()]) + "}"


def _stringify_list(l: list):
    return "[" + ",".join([f'"{v}"' for v in l]) + "]"


##############################################################################
# Comments #####################################
##############################################################################


def post_comment(mp_url: str, comment: str) -> None:
    """
    Post a comment to the specified MP URL.

    Args:
        mp_url (str): The URL of the MP to which the comment will be posted.
        comment (str): The content of the comment to be posted.

    Returns:
        None
    """
    logger.info("Posting comment to MP")
    payload = {
        "ws.op": "createComment",
        "content": comment,
        "subject": "",
        "review_type": "",
    }
    _lp_post(mp_url, data=payload)


class ReviewVote(enum.Enum):
    APPROVE = "Approve"
    NEEDS_FIXING = "Needs Fixing"
    NEEDS_INFO = "Needs Info"
    ABSTAIN = "Abstain"
    DISAPPROVE = "Disapprove"
    NEEDS_RESUBMITTING = "Needs Resubmitting"
    NONE = ""


def post_review_comment(mp_url, comment: str, review_vote: ReviewVote = ReviewVote.NONE):
    """
    Posts a review comment to the specified merge proposal (MP) URL.

    Args:
        mp_url (str): The URL of the merge proposal to post the comment to.
        comment (str): The content of the comment to be posted.
        review_vote (ReviewVote, optional): The vote associated with the review comment. Defaults to ReviewVote.NONE.

    Returns:
        None
    """
    logger.info(f"Posting review comment to MP with vote '{review_vote.value}'")
    payload = {
        "ws.op": "createComment",
        "content": comment,
        "subject": "",
        "review_type": "",
        "vote": review_vote.value,
    }
    _lp_post(mp_url, data=payload)


def parse_comment(comment: dict) -> dict:
    # @dataclasses.dataclass
    # class MergeProposalCommentType:
    #     id: str
    #     self_link: str
    #     author: str
    #     message: str
    #     date_created: str
    #     date_last_edited: Optional[str] = None
    #     title: Optional[str] = None
    #     vote: Optional[str] = None
    #     vote_tag: Optional[str] = None

    #     {
    # 'as_quoted_email': '> FAILED: Continuous integration, '
    #                     'rev:eca64bc0ed8afabef2b0170eb3c84534d7b3b541\n'
    #                     '> '
    #                     'https://stable-cloud-images-jenkins.canonical.com/job/maint-ci-cloudware-\n'
    #                     '> ibmlib-test/1/\n'
    #                     '> Executed test runs:\n'
    #                     '>     None: '
    #                     'https://stable-cloud-images-jenkins.canonical.com/job/maint-ci-\n'
    #                     '> vote/1799/\n'
    #                     '> \n'
    #                     '> \n'
    #                     '> Click here to trigger a rebuild:\n'
    #                     '> '
    #                     'https://stable-cloud-images-jenkins.canonical.com/job/maint-ci-cloudware-\n'
    #                     '> ibmlib-test/1//rebuild',
    #  'author_link': 'https://api.launchpad.net/devel/~cpc-ci-bot',
    #  'branch_merge_proposal_link': 'https://api.launchpad.net/devel/~a-dubs/cloudware/+git/ibmlib/+merge/452408',
    #  'content': 'FAILED: Continuous integration, '
    #             'rev:eca64bc0ed8afabef2b0170eb3c84534d7b3b541\n'
    #             'https://stable-cloud-images-jenkins.canonical.com/job/maint-ci-cloudware-ibmlib-test/1/\n'
    #             'Executed test runs:\n'
    #             '    None: '
    #             'https://stable-cloud-images-jenkins.canonical.com/job/maint-ci-vote/1799/\n'
    #             '\n'
    #             '\n'
    #             'Click here to trigger a rebuild:\n'
    #             'https://stable-cloud-images-jenkins.canonical.com/job/maint-ci-cloudware-ibmlib-test/1//rebuild',
    #  'date_created': '2023-09-28T19:15:47.346961+00:00',
    #  'date_deleted': None,
    #  'date_last_edited': None,
    #  'http_etag': '"482e24936ae24cb79277193ad637329739857bc2-dd7d2d8fc125d74df1e4651c96dd7fbd7464a8fe"',
    #  'id': 1209630,
    #  'message_body': 'FAILED: Continuous integration, '
    #                  'rev:eca64bc0ed8afabef2b0170eb3c84534d7b3b541\n'
    #                  'https://stable-cloud-images-jenkins.canonical.com/job/maint-ci-cloudware-ibmlib-test/1/\n'
    #                  'Executed test runs:\n'
    #                  '    None: '
    #                  'https://stable-cloud-images-jenkins.canonical.com/job/maint-ci-vote/1799/\n'
    #                  '\n'
    #                  '\n'
    #                  'Click here to trigger a rebuild:\n'
    #                  'https://stable-cloud-images-jenkins.canonical.com/job/maint-ci-cloudware-ibmlib-test/1//rebuild',
    #  'owner_link': 'https://api.launchpad.net/devel/~cpc-ci-bot',
    #  'resource_type_link': 'https://api.launchpad.net/devel/#code_review_comment',
    #  'revisions_collection_link': 'https://api.launchpad.net/devel/~a-dubs/cloudware/+git/ibmlib/+merge/452408/comments/1209630/revisions',
    #  'self_link': 'https://api.launchpad.net/devel/~a-dubs/cloudware/+git/ibmlib/+merge/452408/comments/1209630',
    #  'title': 'Comment on proposed merge of '
    #           '~a-dubs/cloudware/+git/ibmlib:CPC-2963-add-ibm-guest into '
    #           '~cloudware/cloudware/+git/ibmlib:devel',
    #  'vote': 'Needs Fixing',
    #  'vote_tag': 'continuous-integration',
    #  'web_link': 'https://code.launchpad.net/~a-dubs/cloudware/+git/ibmlib/+merge/452408/comments/1209630'
    #  }

    return {
        "id": comment["id"],
        "self_link": comment["self_link"],
        "author_name": comment["author_link"].split("/~")[-1],
        "author_link": comment["author_link"],
        "message": comment["content"],
        "date_created": comment["date_created"],
        "date_last_edited": comment["date_last_edited"],
        "title": comment["title"],
        "vote": comment["vote"],
        "vote_tag": comment["vote_tag"],
        "revision_api_collection_link": comment["revisions_collection_link"],
    }


def get_comments(mp_url) -> list[dict]:
    # In case the URL ends with a slash, remove it
    url = f"{mp_url.rstrip('/')}/all_comments"
    r = _lp_get(url)
    return [parse_comment(comment) for comment in r["entries"]]


##############################################################################
# Inline Comments ################################
##############################################################################


def get_draft_inline_comments(mp_url, preview_diff_id) -> dict[str, str]:
    """
    Fetch draft inline comments for a preview diff.

    Returns:
        Dictionary of draft inline comments.
        Example: {'14': 'asdfsafd', '91': 'manual test'}
    """
    api_url = f"{mp_url}?ws.op=getDraftInlineComments&previewdiff_id={preview_diff_id}"
    r = _lp_get(api_url)
    if r is None:
        logger.info("No draft inline comments found")
        return {}
    logger.info(f"Found {len(r.items())} draft inline comments")
    return r


def _put_draft_inline_comments(mp_url, preview_diff_id, comments: dict[str, str]):
    """
    Save draft inline comments for a preview diff.
    """
    logger.info("Putting draft inline comments to LP")
    payload = {
        "ws.op": "saveDraftInlineComment",
        "comments": _stringify_dict(comments),
        "previewdiff_id": preview_diff_id,
    }
    r = _lp_post(mp_url, data=payload)
    # raise an exception if the request failed
    return r


def cancel_inline_draft_comment(mp_url, preview_diff_id, line_no):
    """
    Cancel an existing draft inline comment for a specific line in a preview diff.

    Args:
        mp_url (str): The URL of the merge/pull request.
        preview_diff_id (str): The identifier of the preview diff.
        line_no (int or str): The line number of the draft comment to be cancelled.

    Returns:
        None
    """
    # Fetch existing draft inline comments for the preview diff
    existing_draft_comments = get_draft_inline_comments(mp_url, preview_diff_id)
    logger.info(f"Existing draft comments: {existing_draft_comments}")
    # Check if the draft comment exists for the specified line_no
    if str(line_no) not in existing_draft_comments:
        logger.info(f"Comment does not exist at line {line_no}. Doing nothing.")
        return
    logger.info(f"Draft inline comment exists at line {line_no}. Removing it.")
    # Remove the draft comment for the specified line_no
    del existing_draft_comments[str(line_no)]
    # Update the server with the new list of draft comments
    _put_draft_inline_comments(mp_url, preview_diff_id, existing_draft_comments)


def get_inline_comments(mp_url, preview_diff_id) -> list[dict]:
    get_inline_comments_params = {
        "ws.op": "getInlineComments",
        "previewdiff_id": preview_diff_id,
    }
    r = _lp_get(mp_url, params=get_inline_comments_params)
    logger.info(f"Found {len(r)} inline comments")
    return _simplify_incline_comments(r)


def submit_and_post_inline_comment(mp_url, preview_diff_id, line_no, comment: str, delete_existing_draft: bool = True):
    """
    Post an inline comment to a preview diff at a given line number.

    Args:
        mp_url (str): The merge proposal URL.
        preview_diff_id (str or int): The preview diff ID.
        line_no (str or int): The line number to post the comment at.
        comment (str): The comment to post.
        delete_existing_draft (bool, optional): Whether to delete the existing draft comment at the same line number if it exists.

    Returns:
        None
    """
    # Fetch existing draft comments
    existing_draft_comments = get_draft_inline_comments(mp_url, preview_diff_id)
    logger.info(f"Posting inline comment at line {line_no} with message: {comment}")
    payload = {
        "ws.op": "createComment",
        "content": "",
        "inline_comments": _stringify_dict({str(line_no): comment}),
        "previewdiff_id": preview_diff_id,
    }
    _lp_post(mp_url, data=payload)
    # Remove the draft comment if it exists for the same line_no
    if delete_existing_draft and str(line_no) in existing_draft_comments:
        del existing_draft_comments[str(line_no)]
    elif str(line_no) in existing_draft_comments:
        if existing_draft_comments[str(line_no)] == comment:
            logger.info("Existing draft comment is the same as the new comment. Removing it.")
            del existing_draft_comments[str(line_no)]
    # Restore the draft comments
    _put_draft_inline_comments(mp_url, preview_diff_id, existing_draft_comments)


def save_draft_inline_comment(mp_url, preview_diff_id, line_no, comment: str):
    # Fetch existing draft inline comments for the preview diff
    existing_draft_comments = get_draft_inline_comments(mp_url, preview_diff_id)
    # Add or update the draft comment at the given line_no
    if str(line_no) not in existing_draft_comments:
        logger.info(f"Adding new draft comment at line {line_no}")
        existing_draft_comments[str(line_no)] = comment
    else:
        logger.info(f"Updating draft comment at line {line_no}")
        existing_draft_comments[str(line_no)] = comment
    _put_draft_inline_comments(mp_url, preview_diff_id, existing_draft_comments)


def _simplify_incline_comments(inline_comments: list[dict]) -> list[dict]:
    """
    Simplifies the inline comments data structure by simplifying the author data.
    """
    return [
        {
            "date": comment["date"],
            "line_number": comment["line_number"],
            "author": _simplify_person_dict(comment["person"]),
            "text": comment["text"],
        }
        for comment in inline_comments
    ]


def _simplify_person_dict(person_dict):
    return {
        "name": person_dict["name"],
        "display_name": person_dict["display_name"],
        "description": person_dict["description"],
        "web_link": person_dict["web_link"],
        "self_link": person_dict["self_link"],
        "logo_link": person_dict["logo_link"],
        "mugshot_link": person_dict["mugshot_link"],
    }

from pydantic import BaseModel, Field

class Person(BaseModel):
    name: str
    display_name: str
    description: str
    web_link: str
    self_link: str
    logo_link: str
    mugshot_link: str

    @classmethod
    def from_dict(cls, person_dict):
        return cls(
            name=person_dict["name"],
            display_name=person_dict["display_name"],
            description=person_dict["description"],
            web_link=person_dict["web_link"],
            self_link=person_dict["self_link"],
            logo_link=person_dict["logo_link"],
            mugshot_link=person_dict["mugshot_link"],
        )

##############################################################################


def get_preview_diff_text(
    mp_url: str,
    preview_diff_id: Union[int, str],
) -> str:
    diff_text_url = f"{mp_url}/+preview-diff/{preview_diff_id}/diff_text"
    r = _lp_get(diff_text_url)
    return r.content.decode("utf-8")


# def get_review_votes


class MergeProposalApiObject(BaseModel):
    """
    Represents a Merge Proposal object from the Launchpad API
    """
    commit_message: Optional[str]
    date_created: str
    date_merged: Optional[str]
    date_review_requested: Optional[str]
    description: Optional[str]
    preview_diff_link: str = Field(description="Link to the most recent/current preview diff")
    private: bool
    status: Literal["Needs review", "Approved", "Merged", "Rejected", "Work in progress"]
    author_link: str
    self_link: str
    source_git_repository_link: str
    target_git_repository_link: str
    web_link: str

    @property
    def all_comments_collection_link(self):
        return f"https://api.launchpad.net/devel/{self.self_link}/all_comments"
    
    @property
    def preview_diffs_collection_link(self):
        return f"https://api.launchpad.net/devel/{self.self_link}/preview_diffs"
    
    @property
    def votes_collection_link(self):
        return f"https://api.launchpad.net/devel/{self.self_link}/votes"

    @classmethod
    def from_api_response(cls, mp: dict):
        try:
            return cls(
                commit_message=mp["commit_message"],
                date_created=mp["date_created"],
                date_merged=mp["date_merged"],
                date_review_requested=mp["date_review_requested"],
                description=mp["description"],
                preview_diff_link=mp["preview_diff_link"],
                private=mp["private"],
                status=mp["queue_status"],
                author_link=mp["registrant_link"],
                self_link=mp["self_link"],
                source_git_repository_link=mp["source_git_repository_link"],
                target_git_repository_link=mp["target_git_repository_link"],
                web_link=mp["web_link"],
            )
        except Exception as e:
            # print(f"Error parsing MP object: {e} for mp with url {mp['web_link']}")
            return None
        
def get_merge_proposal(mp_url: str) -> MergeProposalApiObject:
    r = _lp_get(mp_url)
    return MergeProposalApiObject(**r)


# get currently authenticated user
# GET /1.0/people/+me 
def get_current_user() -> Person:
    r = _lp_get("https://api.launchpad.net/devel/people/+me")
    return Person.from_dict(r)


def get_project(project_name):
    url = f"https://api.launchpad.net/devel/{project_name}"
    return _lp_get(url, verbose=False)


def batch(iterable, n=1):
    it = iter(iterable)
    while batch := list(islice(it, n)):
        yield batch


def fetch_all_mps_in_batches(mp_urls, batch_size=5, num_diffs=1) -> list[MergeProposalApiObject]:
    all_mps = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for mp_url_batch in batch(mp_urls, batch_size):
            futures = [executor.submit(get_merge_proposal, mp_url) for mp_url in mp_url_batch]
            for future in concurrent.futures.as_completed(futures):
                try:
                    mp_result = future.result()
                    all_mps.append(mp_result)
                except Exception as exc:
                    print(f"Fetching MP generated an exception: {exc}")
    return all_mps


def _paginate_lp_collection(collection_url, params={}):
    r = _lp_get(collection_url, params=params)
    entries = r["entries"]
    if "next_collection_link" in r:
        next_url = r["next_collection_link"]
        while next_url:
            r = _lp_get(next_url)
            entries.extend(r["entries"])
            if "next_collection_link" in r:
                next_url = r["next_collection_link"]
            else:
                next_url = None
    return entries


def _fetch_mps_json_from_api_for_project(project_name, status: Optional[str] = None) -> list[dict[str, any]]:
    url = f"https://api.launchpad.net/devel/{project_name}"
    params = {
        "ws.op": "getMergeProposals",
    }
    if status:
        params["status"] = status

    # use the paginate helper 
    return _paginate_lp_collection(url, params)
    
def get_basic_mps_info_for_project(project_name: str, status: str = "Needs review") -> list[MergeProposalApiObject]:
    mps = _fetch_mps_json_from_api_for_project(project_name, status=status)
    return [mp_obj for mp in mps if (mp_obj := MergeProposalApiObject.from_api_response(mp))]

def get_team(team_name):
    url = f"https://api.launchpad.net/devel/~{team_name}"
    r = _lp_get(url, verbose=False)
    r["members"] = _paginate_lp_collection(r["participants_collection_link"])
    return r