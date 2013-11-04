#!/usr/bin/python

import httplib2
import pprint
import sys
import gflags
import re

FLAGS = gflags.FLAGS

from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file   import Storage
from oauth2client.tools  import run

def main():
    requester = httplib2.Http(".cache")
    try:
        response, content = requester.request(sys.argv[1], "GET")
    except:
        print "Usage: %s url" % sys.argv[0]
        sys.exit(0)
    videos = getIDsFromPage(content)
    youtube = getAuth()
    # first create playlist with appropriate title+desc
    part = 1
    newPlaylistResp = createPlaylist(youtube, "Autogenerated playlist pt %s" % part, 
    "Generated from url %s" % sys.argv[1])
    playlistID = newPlaylistResp["id"]
    # now start inserting videos
    for rId in videos:
        try:
            print "Adding video with id %s to playlist..." % rId
            insertResponse = addVideo(youtube, rId, playlistID)
        except Exception as e:
            if re.search("Playlist contains max", str(e)):
                if part > 3:
                    print "Definitely too many playlists created, exiting..."
                    sys.exit(0)
                part += 1
                print "Creating new playlist, old one full:"
                newPlaylistResp = createPlaylist(youtube, "Autogenerated playlist pt %s" % part, 
                "Generated from url %s" % sys.argv[1])
                playlistID = newPlaylistResp["id"]
            """youtube.playlists().delete(
                    id=playlistID
                ).execute()"""
            print e
            #sys.exit(0)

def createPlaylist(auth, title, desc):
    response = auth.playlists().insert(
        part="snippet,status",
        body=dict(
            snippet=dict(
                title=title,
                description=desc
            ),
            status = dict(
                privacyStatus="private"
            )
        )
    ).execute()
    return response

def addVideo(auth, rId, playlistID): 
    insertResponse = auth.playlistItems().insert(
        part="snippet",
        body=dict(
            snippet=dict(
                playlistId=playlistID,
                resourceId=dict(
                    kind="youtube#video",
                    videoId=rId
                )
            )
        )
    ).execute()
    return insertResponse


def getIDsFromPage(content):
    videos = []
    # This bit on comments is specifically for reddit, so no sidebar links are grabbed.
    comments = False
    for line in content.split('\n'):
        if not re.search("youtube\.com/watch\?", line):
            continue
        if re.search("class=\"sitetable nestedlisting\"", line):
            comments = True
        #if not comments:
            #continue
        line = re.sub(r'.*?<a href="http://www\.youtube\.com/watch',
            'http://www.youtube.com/watch',line)
        line = re.sub(r'">.*?<.*$','',line)
        line = re.sub(r'" rel="nofollow','',line)
        # this gets us the URL, the resourceID is the bit after the v=
        rId = re.search(r'\?v=.{11}',line)
        try:
            rId = rId.group()
        except Exception as e:
            print "Probably no video found here: "+line
            continue 
        rId = re.sub(r'\?v=','',rId)
        videos.append(rId)
    return videos

def getAuth():
    # uses OAuth2 to authorise then authenticate this command line program
    flow = flow_from_clientsecrets(
      'client_secrets.json',
      message="""Please configure OAuth2: You need to create a file in the
      current directory called client_secrets.json and populate it with
      information from the API console here: 
      https://code.google.com/apis/console#access""",
      scope='https://www.googleapis.com/auth/youtube')

    storage = Storage("credstorage.json")
    credentials = storage.get()
    if credentials is None or credentials.invalid:
        credentials = run(flow,storage)

    http = httplib2.Http()
    http = credentials.authorize(http)

    youtube = build('youtube', 'v3', http=http)
    return youtube

if __name__ == '__main__':
    main()


