import logging
import praw
import azure.functions as func
import os


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    commentId = ""
    cvData    = ""
    imageURL  = ""
    try:
        req_body = req.get_json()
    except ValueError:
        pass
    else:
        commentId = req_body.get('commentId')
        cvData    = req_body.get('cvdata')        
        imageURL  = req_body.get('imageUrl')

    reddit = praw.Reddit(
        client_id = os.environ["rclient_id"],
        client_secret = os.environ["rclient_secret"],
        username = os.environ["rusername"],
        password = os.environ["rpassword"],
        user_agent = os.environ["ruser_agent"],
    )    

    predMap = {}
    pred = cvData.get('predictions')
    for predObj in pred:
        prob = predObj.get("probability")
        tag = predObj.get("tagName")
        predMap[tag] = prob

    predId = cvData.get("id")
    predIt = cvData.get("iteration")

    predRes = ""
    probRes = ""
    if (float(predMap["nomold"]) > float(predMap["mold"])):
        predRes = "Not Mold"
        probRes = predMap["nomold"]*100
    else:
        predRes = "Mold"
        probRes = predMap["mold"]*100


    respStr = " Beep Boop Bop, I'm a bot created to help you identify mold in your kombucha! \n\n"
#    respStr = respStr + "Based on your image " + imageURL + ", \n\n"
    respStr = respStr + "&nbsp; \n\n"
    respStr = respStr + "Based on your image, I predict this is **" + predRes + "** with a probability of **" + str(probRes) + "%**. \n\n"
    respStr = respStr + "&nbsp; \n\n"
    respStr = respStr + "You can call me to evaluate your image by Including my name in the this format **!KombuchMoldBot**  \n\n"
    respStr = respStr + "* in a comment with an image url (.jpg, .jpeg, .bmp).  \n"
    respStr = respStr + "* or in the child of a comment with an image url.  \n"
    respStr = respStr + "* or in a top level comment on a post that links to an image.  \n\n"
    respStr = respStr + "&nbsp; \n\n"
    respStr = respStr + "Please upvote/downvote my responses to help train my models. \n\n"
    respStr = respStr + "***  \n"
#    respStr = respStr + "I'm built and run on Microsoft Azure PaaS and Azure Custom Computer Vision.  Find out more about me [here](http://empty)  \n\n"
    respStr = respStr + "*id: " + predId + "*  \n"
    respStr = respStr + "*iteration: " + predIt + "*  \n"

    comment = reddit.comment(commentId)
    comment.reply(respStr)

    return func.HttpResponse(
            "This HTTP triggered function executed successfully",
            status_code=200
    )
