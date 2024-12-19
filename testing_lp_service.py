# Testing all inline comment functions #################

# mp_url = "https://code.launchpad.net/~a-dubs/cloudware/+git/oraclelib/+merge/455155"
# preview_diff_id = "1055515"
# draft_ilc = get_draft_inline_comments(
#     mp_url=mp_url,
#     preview_diff_id=preview_diff_id
# )
# print("Original draft inline comments:")
# pprint(draft_ilc)

# # get first entry in draft_ilc
# target_line_no, target_comment = list(draft_ilc.items())[0]
# print("Target line no:", target_line_no)
# print("Target comment:", target_comment)

# # cancel the draft comment
# cancel_inline_draft_comment(mp_url, preview_diff_id, target_line_no)
# # print out the draft comments again to verify that the draft comment was removed
# draft_ilc = get_draft_inline_comments(
#     mp_url=mp_url,
#     preview_diff_id=preview_diff_id
# )
# print("After cancelling the draft comment:")
# pprint(draft_ilc)

# # now resave the draft comment
# save_draft_inline_comment(mp_url, preview_diff_id, target_line_no, target_comment)
# # print out the draft comments again to verify that the draft comment was added back
# draft_ilc = get_draft_inline_comments(
#     mp_url=mp_url,
#     preview_diff_id=preview_diff_id
# )
# print("After resaving the draft comment:")
# pprint(draft_ilc)

# # now update the draft comment with new message
# new_content = target_comment + " :)"
# save_draft_inline_comment(mp_url, preview_diff_id, target_line_no, new_content)

# # print out the draft comments again to verify that the draft comment was updated
# draft_ilc = get_draft_inline_comments(
#     mp_url=mp_url,
#     preview_diff_id=preview_diff_id
# )
# print("After updating the draft comment:")
# pprint(draft_ilc)

# # show the inline comments
# ilc = get_inline_comments(
#     mp_url=mp_url,
#     preview_diff_id=preview_diff_id
# )
# print("original inline comments:")
# pprint(ilc)

# print("Posting new inline comment at line with existing comment to see what happens")
# # now post a new inline comment at existing comment line to see what happens
# submit_and_post_inline_comment(mp_url, preview_diff_id, target_line_no, "posting this immediately without saving as draft")

# # show the inline comments again to see if the new comment was added
# ilc = get_inline_comments(
#     mp_url=mp_url,
#     preview_diff_id=preview_diff_id
# )
# print("After posting new inline comment:")
# pprint(ilc)

# # now get draft comments again to see if the draft comment was removed at the line_no that the new comment was
# # posted
# draft_ilc = get_draft_inline_comments(
#     mp_url=mp_url,
#     preview_diff_id=preview_diff_id
# )
# print("After posting new inline comment, draft comments:")
# pprint(draft_ilc)

from pprint import pprint
from diskcache import Cache
from lp_microservice import lp_service


mp_url = "https://code.launchpad.net/~a-dubs/cloudware/+git/oraclelib/+merge/455155"
lp_service.perform_authentication()

# # mp_url = "https://code.launchpad.net/~a-dubs/cloudware/+git/cpc_jenkins/+merge/466022"

# inline_comments = lp_service.get_inline_comments(mp_url, "1055515")
# comments = lp_service.get_comments(mp_url)["entries"]

# # find inline comments with "posting this immediately without saving as draft" as text and print out their date_created
# print("inline_comments")
# for comment in inline_comments:
#     if comment["text"] == "posting this immediately without saving as draft":
#         print(comment["date"])

# # print out all dates of comments with "[ Added inline comment via launchpyd ]" as message_body
# print ("comments")
# for comment in comments:
#     if comment["message_body"] == "[ Added inline comment via launchpyd ]":
#         print(comment["date_created"])


# r = lp_service.get_preview_diff_text(mp_url, "1055515")
# print(x := r[400:600])

# # create cache in local directory
# test_cache = Cache(".test_cache")

# test_cache.set("r", r)
# print(y := test_cache.get("r")[400:600])
# print(x == y)

# r =lp_service.create_webhook_for_repo(
#     repo_url="https://code.launchpad.net/~cloudware/cloudware/+git/cpc_jenkins",
#     webhook_url="https://webhook.site/6957cd78-bae1-4974-9079-e7dc3fa680da",
# )
# print(r)

# r = lp_service.get_repo("https://code.launchpad.net/~a-dubs/cloudware/+git/oraclelib")
# pprint(r)

# r = lp_service._lp_get("https://api.launchpad.net/devel/~cloudware/cloudware/+git/oraclelib/webhooks")

# pprint(r)

