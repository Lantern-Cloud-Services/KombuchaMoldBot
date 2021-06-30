import logging
import praw
import re
import azure.functions as func
import calendar
import time
import requests
import os
import json


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        # app config
        replyToTitles      = eval(os.environ["replyToTitles"])
        titleSearchText    = os.environ["titleSearchText"]
        replyToSelfText    = eval(os.environ["replyToSelfText"])
        selfTextSearchText = os.environ["selfTextSearchText"]
        replyToComments    = eval(os.environ["replyToComments"])
        commentSearchText  = os.environ["commentSearchText"]
        postLimit          = int(os.environ["postLimit"])
        laEndpoint         = os.environ["laEndpoint"]

        prevRepJson = ""
        subReddToMonitor = ""
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            prevRepJson = req_body.get('prevReps')
            subReddToMonitor = req_body.get('subreddit')

        reddit = praw.Reddit(
            client_id = os.environ["rclient_id"],
            client_secret = os.environ["rclient_secret"],
            username = os.environ["rusername"],
            password = os.environ["rpassword"],
            user_agent = os.environ["ruser_agent"],
        )    
        subreddit = reddit.subreddit(subReddToMonitor)

        for submission in subreddit.new(limit=postLimit):
            logging.info("---------------------------------\n")
            logging.info("Id: " + submission.id)
            logging.info("Url: " + submission.url)
            logging.info("Title: " + submission.title)
            logging.info("Text: " + submission.selftext)
            logging.info("Score: " + str(submission.score))
            logging.info(" ")
        
            postData = []
            if replyToTitles:
                postDatea = processReplyToTitle(titleSearchText, submission)
                continue

            if replyToSelfText:
                postData = processReplyToSelftext(selfTextSearchText, submission)
                continue

            if replyToComments:
                repliedComments = []
                if (prevRepJson != None):
                    for commentJson in prevRepJson:
                        commentId = commentJson.get('commentId')
                        if commentId != "":
                            repliedComments.append(commentId)

                postData = processReplyToComment(commentSearchText, submission, repliedComments, subReddToMonitor)

                # postData to LA
                for data in postData:
                    logging.info("Queueing data for process: \n" + json.dumps(data, indent=4, sort_keys=True))
                    response = requests.post(laEndpoint, json=data)



    except Exception as exception:
        logging.error("Error: " + str(exception))
        raise exception

    return func.HttpResponse(
            "This HTTP triggered function executed successfully.",
            status_code=200
        )

def isImagePresent(text):
    return re.search("http", text, re.IGNORECASE) \
    and (re.search(".jpg", text, re.IGNORECASE) \
    or re.search(".jpeg", text, re.IGNORECASE) \
    or re.search(".png", text, re.IGNORECASE))

def createPostMetadata(subId, type, comId, iUrl, subReddToMonitor):
    gmt = time.gmtime()
    
    replyPostData = {
        "subreddit": subReddToMonitor,
        "created": calendar.timegm(gmt),
        "submissionId": subId,
        "replyType": type, # title/selftext/comment
        "commentId": comId,
        "imageUrl": iUrl
    }
    return replyPostData

def parseImageURI(text):
    startInt = text.find("http")

    if re.search(".jpg", text, re.IGNORECASE):
        endInt = text.find(".jpg") + 4
    elif (re.search(".jpeg", text, re.IGNORECASE)):
        endInt = text.find(".jpeg") + 5
    elif (re.search(".png", text, re.IGNORECASE)):
        endInt = text.find(".png") + 4

    return text[startInt:endInt]


# bot was called by title
def processReplyToTitle(titleSearchText, submission):
    if re.search(titleSearchText, submission.title, re.IGNORECASE):

        if submission.url != "" and isImagePresent(submission.url):
            return createPostMetadata(submission.id, "title", "", submission.url)                    
        else:
            # no identified, reply to the post
            logging.info("Bot replying to title for post id: " + submission.id)

# bot was called by selfText
def processReplyToSelftext(selfTextSearchText, submission):
    if submission.selftext != ""  and re.search(selfTextSearchText, submission.selftext, re.IGNORECASE):
        if isImagePresent(submission.selftext):
            logging.info("Bot replying to selftext for post id: " + submission.id)
        else:
            # no identified, reply to the post
            logging.info("Bot replying to selftext for post id: " + submission.id)

def processReplyToComment(commentSearchText, submission, repliedComments, subReddToMonitor):
    imageCommentMap = {}
    postReplyList = []

    submission.comments.replace_more(limit=None)
    for comment in submission.comments.list():
        if comment.author == "KombuchaMoldBot":
            continue

        # bot was called by comment
        if comment.body != "" and re.search(commentSearchText, comment.body, re.IGNORECASE):
                
            # Either initial comment contains an image
            if isImagePresent(comment.body):
                logging.info("Found image in comment with my name")
                if (not repliedComments.__contains__(comment.id)):
                    #comment.reply("beep bop boop - checking image in parent comment")
                    imgUrl = parseImageURI(comment.body)
                    postReplyList.append(createPostMetadata(submission.id, "comment", comment.id, imgUrl, subReddToMonitor))

            # Parent comment contains image
            elif(imageCommentMap.__contains__(comment.parent_id)):                
                logging.info("Found image in parent of comment with my name ")
                if (not repliedComments.__contains__(comment.id)):
                    #comment.reply("beep bop boop - checking image in grandparent comment")
                    imgUrl = imageCommentMap[comment.parent_id]
                    postReplyList.append(createPostMetadata(submission.id, "comment", comment.id, imgUrl, subReddToMonitor))

            # Post URL contains image
            elif (comment.depth == 0) and (isImagePresent(submission.url)):
                logging.info("Found image in url of post with comment that contains my name ")
                if (not repliedComments.__contains__(comment.id)):
                    #comment.reply("beep bop boop - checking image in post URL")
                    postReplyList.append(createPostMetadata(submission.id, "comment", comment.id, submission.url, subReddToMonitor))

            logging.info("Bot replying to post/comment id: " + submission.id + "/" + comment.id)
        else:
            if isImagePresent(comment.body):
                parentId = "t" + str(comment.depth) + "_" + comment.id
                if (comment.depth == 0):
                    parentId = "t1" + "_" + comment.id
                
                imgUrl = parseImageURI(comment.body)
                imageCommentMap[parentId] = imgUrl

    logging.info("Comments Processed")
    return postReplyList