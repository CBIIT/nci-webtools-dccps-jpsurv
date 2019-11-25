import json
import math
import os
import rpy2.robjects as robjects
import smtplib
import time
import logging
import urllib.request, urllib.parse, urllib.error
import sys

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from twisted.internet import reactor, defer
from PropertyUtil import PropertyUtil
from stompest.async import Stomp
from stompest.async.listener import SubscriptionListener
from stompest.async.listener import DisconnectListener
from stompest.config import StompConfig
from stompest.protocol import StompSpec
from rpy2.robjects import r

class jpsurvProcessor(DisconnectListener):
  CONFIG = 'queue.config'
  NAME = 'queue.name'
  URL = 'queue.url'

  def composeMail(self,recipients,message,files=[]):
    config = PropertyUtil(r"config.ini")
    logging.info("sending message")
    if not isinstance(recipients,list):
      recipients = [recipients]
    packet = MIMEMultipart()
    packet['Subject'] = "JPsurv Analysis Results"
    packet['From'] = "JPSurv Analysis Tool <do.not.reply@nih.gov>"
    packet['To'] = ", ".join(recipients)
    logging.info(recipients)
    # print message
    packet.attach(MIMEText(message,'html'))
    for file in files:
      with open(file,"rb") as openfile:
        packet.attach(MIMEApplication(
          openfile.read(),
          Content_Disposition='attachment; filename="%s"' % os.path.basename(file),
          Name=os.path.basename(file)
        ))
    MAIL_HOST=config.getAsString('mail.host')
    logging.info(MAIL_HOST)
    smtp = smtplib.SMTP(MAIL_HOST)
    smtp.sendmail("do.not.reply@nih.gov",recipients,packet.as_string())

  def testQueue(self):
    logging.debug("tested")

  def rLength(self, tested):
    if tested is None:
      return 0
    if isinstance(tested,list) or isinstance(tested,set):
      return len(tested)
    else:
      return 1

 # @This is teh consume code which will listen to Queue server.
  def consume(self, client, frame):
    logging.info("In consume")
    files=[]
    product_name = "JPSurv Analysis Tool"
    parameters = json.loads(frame.body)
    logging.info(parameters)
    token=parameters['token']
    filepath=parameters['filepath']
    timestamp=['timestamp']

    logging.debug(token)
    fname=filepath+"/input_"+token+".json"
    logging.info(fname)
    with open(fname) as content_file:
      jpsurvDataString = content_file.read()

    data=json.loads(jpsurvDataString)
    logging.debug(data)
    try:
      r.source('JPSurvWrapper.R')
      logging.debug("Calculating")
      r.getFittedResultWrapper(parameters['filepath'], jpsurvDataString)
      logging.debug("making message")
      url=urllib.parse.unquote(data['queue']['url'])
      success = True
    except:
      logging.error("calculation failed")
      url=urllib.parse.unquote(data['queue']['url'])
      logging.error(url)
      url=url+"&calculation=failed"
      success = False

    Link='<a href='+url+'> Here </a>'
    logging.info(parameters['timestamp'])
    logging.info("Here is the Link to the past:")
    logging.info(Link)
    
    header = """<h2>"""+product_name+"""</h2>"""
    if success == True:
      body = """
            <div style="background-color:white;border-top:25px solid #142830;border-left:2px solid #142830;border-right:2px solid #142830;border-bottom:2px solid #142830;padding:20px">
              Hello,<br>
              <p>Here are the results you requested on """+parameters['timestamp']+""" from the """+product_name+""".</p>
              <p>
              <div style="margin:20px auto 40px auto;width:200px;text-align:center;font-size:14px;font-weight:bold;padding:10px;line-height:25px">
                <div style="font-size:24px;"><a href='"""+url+"""'>View Results</a></div>
              </div>
              </p>
              <p>The results will be available online for the next 14 days.</p>
            </div>
            """
    else:
      if 'data' in data['file']:
        uploadFiles = data['file']['dictionary'] + " " + data['file']['data']
      else :
        uploadFiles = data['file']['dictionary']
      body = """
            <div style="background-color:white;border-top:25px solid #142830;border-left:2px solid #142830;border-right:2px solid #142830;border-bottom:2px solid #142830;padding:20px">
              Dear User,<br>
              <p>
                  Thanks for using the JPSurv Analysis Tool. Unfortunately the job you submitted to the JPSurv processor failed to be processed. 
                  Please review your dataset to make sure it conforms to the Input Data File format as described in the Help page of the web tool. 
                  Please resubmit your data set after the corrections are made.
              </p>
              <p style="margin-left: 1rem;">
                  Job Information<br>
                  Input Data File: """+uploadFiles+"""<br>
                  Submitted Time: """+parameters['timestamp']+"""
              </p>
              <p>JPSurv Web admin</p>
            </div>
            """

    footer = """
          <div>
            <p>
              (Note:  Please do not reply to this email. If you need assistance, please contact NCIJPSurvWebAdmin@mail.nih.gov)
            </p>
          </div>

            <div style="background-color:#ffffff;color:#888888;font-size:13px;line-height:17px;font-family:sans-serif;text-align:left">
                  <p>
                      <strong>About <em>"""+product_name+"""</em></strong></em><br>
                      The JPSurv software has been developed to analyze trends in survival with respect to year at diagnosis. Survival data includes two temporal dimensions that are important to account for: the calendar year at diagnosis and the time since diagnosis. The JPSurv fits a Joinpoint survival model(1) to the hazard of cancer death by year at diagnosis and assumes a common baseline hazard by time since diagnosis. In other words, the probabilities of dying at different time interval, e.g., 0 to 1 year, 1 to 2 years, 2 to 3 years, and 4 to 5 years since diagnosis are proportional and share the same joinpoints. The software uses discrete-time survival data, i.e. survival data grouped by years since diagnosis in the life table format. The software accommodates both relative survival and cause-specific survival.
                      <br>
                      The JPSurv tool is useful to estimate when and how much survival changed over time and to predict survival into the future for simulation studies and scenario analyses.
                      <br>
                      1. Yu BB, Huang L, Tiwari RC, Feuer EJ, Johnson KA. Modelling population-based cancer survival trends by using join point models for grouped survival data. Journal of the Royal Statistical Society Series a-Statistics in Society. 2009;172:405-25.
                      <br>
                      <strong>For more information, visit
                        <a target="_blank" style="color:#888888" href="https://analysistools.nci.nih.gov/jpsurv">analysistools.nci.nih.gov/jpsurv</a>
                      </strong>
                  </p>
                  <p style="font-size:11px;color:#b0b0b0">If you did not request a calculation please ignore this email.
    Your privacy is important to us.  Please review our <a target="_blank" style="color:#b0b0b0" href="http://www.cancer.gov/policies/privacy-security">Privacy and Security Policy</a>.
  </p>
                  <p align="center"><a href="http://cancercontrol.cancer.gov/">Division of Cancer Control & Population Sciences</a>,
                  <span style="white-space:nowrap">a Division of <a href="www.cancer.gov">National Cancer Institute</a></span><br>
                  BG 9609 MSC 9760 | 9609 Medical Center Drive | Bethesda, MD 20892-9760 | <span style="white-space:nowrap"><a target="_blank" value="+18004006916" href="tel:1-800-422-6237">1-800-4-CANCER</a></span>
                  </p>
                </div>
                """
    message = """
      <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <title>html title</title>
      </head>
      <body>"""+header+body+footer+"""</body>"""

          #    "\r\n\r\n - JPSurv Team\r\n(Note:  Please do not reply to this email. If you need assistance, please contact xxxx@mail.nih.gov)"+
          #    "\n\n")
    self.composeMail(data['queue']['email'],message,files)
    logging.info("end")

  @defer.inlineCallbacks
  def run(self):
    client = Stomp(self.config)
    yield client.connect()
    headers = {
        # client-individual mode is necessary for concurrent processing
        # (requires ActiveMQ >= 5.2)
        StompSpec.ACK_HEADER: StompSpec.ACK_CLIENT_INDIVIDUAL,
        # the maximal number of messages the broker will let you work on at the same time
        'activemq.prefetchSize': '100',
    }

    client.subscribe(self.QUEUE, headers, listener=SubscriptionListener(self.consume, errorDestination=self.ERROR_QUEUE))
    client.add(listener=self)

  # Consumer for Jobs in Queue, needs to be rewrite by the individual projects

  def onCleanup(self, connect):
    logging.info('In clean up ...')

  def onConnectionLost(self, connect, reason):
    logging.info("in onConnectionLost")
    self.run()

 # @read from property file to set up parameters for the queue.
  def __init__(self, dev_mode = False):
    config = PropertyUtil(r"config.dev.ini" if dev_mode else r"config.ini")
     # Initialize Connections to ActiveMQ
    self.QUEUE=config.getAsString(jpsurvProcessor.NAME)
    self.ERROR_QUEUE=config.getAsString('queue.error.name')
    config = StompConfig(config.getAsString(jpsurvProcessor.URL))
    self.config = config

if __name__ == '__main__':
  from argparse import ArgumentParser
  parser = ArgumentParser()
  parser.add_argument('-d', '--debug', action = 'store_true')
  parser.add_argument('port', nargs='+')
  args = parser.parse_args()

  logging.basicConfig(level=logging.INFO, filename='../logs/queue.log', filemode='w')
  logging.info("JPSurv processor has started")
  jpsurvProcessor(dev_mode = args.debug).run()
  reactor.run()
