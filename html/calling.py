from twilio.rest import TwilioRestClient
import urllib2
import time

# put your own credentials here
ACCOUNT_SID = "AC5a82efddfe9e845d91fdca45845746a3"
AUTH_TOKEN = "f640157070d38be36ecff7a2b24158f9"


def handler(event, context):
    client = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)
    response = urllib2.urlopen('http://akinaga.cshhage.jp/phone_number.txt')
    html = response.readlines()
    for target in html:
        call = client.calls.create(to=target,
                                   from_="+815031318526",
                                   url="http://twilio.cshhage.jp/voice.xml",
                                   method="GET",
                                   fallback_method="GET",
                                   status_callback_method="GET",
                                   record="false")
        print call.sid
        time.sleep(1)
