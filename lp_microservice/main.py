import os
import sys
from typing import Union
import logging
from lp_microservice.lp_service import (
    perform_authentication,
    get_draft_inline_comments,
    cancel_inline_draft_comment,
    get_inline_comments,
    submit_and_post_inline_comment,
    save_draft_inline_comment,
    get_comments,
    post_review_comment,
    post_comment,
    ReviewVote,
    wait_for_credentials,
    LP_CREDS_PATH,
)

# Initialize the FastAPI app
app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Hello from main.py")

@app.get("/get_draft_inline_comments")
def api_get_draft_inline_comments(mp_url: str, preview_diff_id: Union[str, int]):
    try:
        return get_draft_inline_comments(mp_url, str(preview_diff_id))
    except Exception as e:
        logger.exception("Error in get_draft_inline_comments")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cancel_inline_draft_comment")
def api_cancel_inline_draft_comment(mp_url: str, preview_diff_id: Union[str, int], line_no: Union[str, int]):
    try:
        cancel_inline_draft_comment(mp_url, str(preview_diff_id), str(line_no))
        return {"status": "Draft comment canceled successfully"}
    except Exception as e:
        logger.exception("Error in cancel_inline_draft_comment")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_inline_comments")
def api_get_inline_comments(mp_url: str, preview_diff_id: Union[str, int]):
    try:
        return get_inline_comments(mp_url, str(preview_diff_id))
    except Exception as e:
        logger.exception("Error in get_inline_comments")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/submit_and_post_inline_comment")
def api_submit_and_post_inline_comment(
    mp_url: str,
    preview_diff_id: Union[str, int],
    line_no: Union[str, int],
    comment: str,
    delete_existing_draft: bool = True
):
    try:
        submit_and_post_inline_comment(
            mp_url, str(preview_diff_id), str(line_no), comment, delete_existing_draft
        )
        return {"status": "Inline comment submitted and posted successfully"}
    except Exception as e:
        logger.exception("Error in submit_and_post_inline_comment")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save_draft_inline_comment")
def api_save_draft_inline_comment(mp_url: str, preview_diff_id: Union[str, int], line_no: Union[str, int], comment: str):
    try:
        save_draft_inline_comment(mp_url, str(preview_diff_id), str(line_no), comment)
        return {"status": "Draft inline comment saved successfully"}
    except Exception as e:
        logger.exception("Error in save_draft_inline_comment")
        raise HTTPException(status_code=500, detail=str(e))

# New endpoints

@app.get("/get_comments")
def api_get_comments(mp_url: str):
    try:
        return get_comments(mp_url)
    except Exception as e:
        logger.exception("Error in get_comments")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/post_review_comment")
def api_post_review_comment(mp_url: str, comment: str, review_vote: str = ""):
    try:
        # Cast review_vote to ReviewVote enum, defaulting to NONE if empty
        review_vote_enum = ReviewVote(review_vote) if review_vote else ReviewVote.NONE
        post_review_comment(mp_url, comment, review_vote_enum)
        return {"status": "Review comment posted successfully"}
    except ValueError:
        logger.exception("Invalid review_vote value")
        raise HTTPException(status_code=400, detail="Invalid review vote")
    except Exception as e:
        logger.exception("Error in post_review_comment")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/post_comment")
def api_post_comment(mp_url: str, comment: str):
    try:
        post_comment(mp_url, comment)
        return {"status": "Comment posted successfully"}
    except Exception as e:
        logger.exception("Error in post_comment")
        raise HTTPException(status_code=500, detail=str(e))

def prepare_creds_location():
    logger.debug("Preparing credentials location")
    # use LP_CREDS_PATH
    # create directory if it doesn't exist and set permissions to be writeable by anyone (777)
    os.makedirs(os.path.dirname(LP_CREDS_PATH), exist_ok=True)
    # set permissions to be writeable by anyone (777)
    os.chmod(os.path.dirname(LP_CREDS_PATH), 0o777)

def run_server():
    prepare_creds_location()
    # Poll for the credentials file, waiting until it exists
    logger.info("Checking for authentication credentials...")
    if not wait_for_credentials():
        logger.info("Authentication not completed. Exiting daemon.")
        sys.exit(1)

    # If credentials exist, start the web server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)