import xbmc, xbmcgui
import urllib, urllib2
import re
import HTMLParser
from elementtree.ElementTree import parse

try:
    from addon.common.addon import Addon
    from addon.common.net import Net
except:
    xbmc.log('Failed to import script.module.addon.common, attempting t0mm0.common')
    xbmcgui.Dialog().ok("Import Failure", "Failed to import addon.common", "A component needed by this addon is missing on your system", "Please visit www.xbmc.org for support")


addon = Addon('plugin.video.redlettermedia', sys.argv)
net = Net()

##### Queries ##########
play = addon.queries.get('play', None)
mode = addon.queries['mode']
url = addon.queries.get('url', None)
page_num = addon.queries.get('page_num', None)

addon.log('-----------------RedLetterMedia Addon Params------------------')
addon.log('--- Version: ' + str(addon.get_version()))
addon.log('--- Mode: ' + str(mode))
addon.log('--- Play: ' + str(play))
addon.log('--- URL: ' + str(url))
addon.log('--- Page: ' + str(page_num))
addon.log('---------------------------------------------------------------')


################### Global Constants #################################

MainUrl = 'http://redlettermedia.com/'
APIPath = 'http://blip.tv/players/episode/%s?skin=api'
AddonPath = addon.get_path()
IconPath = AddonPath + "/icons/"

######################################################################


# Temporary function to grab html even when encountering an error
# Some pages on the site return 404 even though the html is there
def get_http_error(url):
    addon.log('--- Requesting URL: ' + str(url))
    req = urllib2.Request(url)
    req.add_header('User-Agent', net._user_agent)
    try:
        response = urllib2.urlopen(req)
        html = response.read()
    except urllib2.HTTPError, error:
        html = error.read()
    
    return html


def get_url(url):
    headers = {
            'Host': 'redlettermedia.com'
        }
    addon.log('--- Requesting URL: ' + str(url))
    h = HTMLParser.HTMLParser() 
    html = net.http_GET(url, headers=headers).content
    html = h.unescape(html)
    return html.encode('utf-8')


if play:

    try:
        import urlresolver
    except:
        addon.log_error("Failed to import script.module.urlresolver")
        xbmcgui.Dialog().ok("Import Failure", "Failed to import URLResolver", "A component needed by this addon is missing on your system", "Please visit www.xbmc.org for support")

    #Check if url is youtube link first
    isyoutube = re.search('youtube.com', url)
    
    if isyoutube:
        stream_url = urlresolver.HostedMediaFile(url).resolve()
    
    #Is a redlettermedia url, so need to find and parse video link
    else:
    
        html = get_url(url)
          
        #First check if there are multiple video parts on the page
        parts = re.compile('>([PARTart]* [1-9]):<br />').findall(html)
        
        #Page has multiple video parts
        if len(parts) > 1:
            partlist = []
            for part in parts:
                partlist.append(part)    
            
            dialog = xbmcgui.Dialog()
            index = dialog.select('Choose the video', partlist)
            
            #Take only selected part portion of the html
            if index >= 0:          
                html = re.search('>%s:<br />(.+?)</p>' % partlist[index],html,re.DOTALL).group(1)
            else:
                html = False
    
        if html:                 
        
            #Check for youtube video first
            youtube = re.search('src="([http:|https:]*//www.youtube.com/[v|embed]*/[0-9A-Za-z_\-]+).+?"',html)
            springboard = re.search('src="(http://cms.springboardplatform.com/.+?)"', html)
            
            if youtube:
                if youtube.group(1).startswith("//"):
                    youtube_link = 'http:' + youtube.group(1)
                else:
                    youtube_link = youtube.group(1)
                stream_url = urlresolver.HostedMediaFile(url=youtube_link).resolve()
            
            elif springboard:
                html = net.http_GET(springboard.group(1)).content
                stream_url = re.search('<meta property="og:video" content="(.+?)" />', html).group(1)
                
            else:
            
                video = re.search('<embed.+?src="http://[a.]{0,2}blip.tv/[^#/]*[#/]{1}([^"]*)"',html, re.DOTALL).group(1)
                api_url = APIPath % video
               
                links = []
                roles = []
                    
                tree = parse(urllib.urlopen(api_url))
                for media in tree.getiterator('media'):
                    for link in media.getiterator('link'):
                        links.append(link.get('href'))
                        roles.append(media.findtext('role'))
                    
                dialog = xbmcgui.Dialog()
                index = dialog.select('Choose a video source', roles)          
                if index >= 0:
                    stream_url = links[index]
                else:
                    stream_url = False
        else:
            stream_url = False
    
    #Play the stream
    if stream_url:
        addon.resolve_url(stream_url)  


def mainpage_links(page):
    addon.add_directory({'mode': 'none'}, {'title': '[COLOR blue]Recent Updates[/COLOR]'}, is_folder=False, img='')
    if int(page) > 1:
        url = MainUrl + 'page/%s/' % page
    else:
        url = MainUrl
    html = get_url(url)
    sections = re.compile('st-[0-9]+ post type-post status-publish format-standard has-post-thumbnail hentry [categorya-z- ]+" id="post-main-[0-9]+">(.+?)(<div class="po|<script)', re.DOTALL).findall(html)
    for section, nothing in sections:
        thumb = ''
        blip_link = re.search('<iframe src="(.+?)"', section)
        if blip_link:
            blip_html = net.http_GET(blip_link.group(1)).content
            icon=re.search('config.video.thumbnail = "(.+?)"', blip_html)
            if icon:
                thumb='http:' + icon.group(1).replace("THUMB_WIDTH", "630").replace("THUMB_HEIGHT", "350")
        entry = re.search('<h2 class="post-title"><a href="(.+?)"[ rel="bookmark"]* title=".+?">(.+?)</a></h2>', section)
        addon.add_video_item({'url': entry.group(1)},{'title':entry.group(2)},img=thumb)
    if re.search('>Next Page', html):
        page = int(page) + 1
        addon.add_directory({'mode': 'main_next_page', 'page_num': page}, {'title': 'Next Page(%s)' % page}, img=IconPath + 'next.png')

if mode == 'main': 
    addon.add_directory({'mode': 'plinkett', 'url': MainUrl}, {'title': 'Plinkett Reviews'}, img=IconPath + 'plinkett.jpg')
    addon.add_directory({'mode': 'halfbag', 'url': MainUrl + 'half-in-the-bag/'}, {'title': 'Half in the Bag'}, img=IconPath + 'halfbag.jpg')
    addon.add_directory({'mode': 'bestworst', 'url': MainUrl + 'best-of-the-worst/'}, {'title': 'Best of the Worst'}, img=IconPath + 'botw-title.jpg')
    addon.add_directory({'mode': 'featurefilms', 'url': MainUrl + 'films/'}, {'title': 'Feature Films'})
    addon.add_directory({'mode': 'shortfilms', 'url': MainUrl + 'shorts/'}, {'title': 'Short Films'})
    mainpage_links(page=1)

elif mode == 'main_next_page':
    mainpage_links(page_num)
    
elif mode == 'plinkett':
    url = addon.queries['url']
    html = get_url(url)
    
    r = re.search('MR. PLINKETT</a>.+?<ul class="sub-menu">(.+?)</ul>', html, re.DOTALL)
    if r:
        match = re.compile('<li.+?><a href="(.+?)">(.+?)</a></li>').findall(r.group(1))
    else:
        match = None

    # Add each link found as a directory item
    for link, name in match:
       addon.add_directory({'mode': 'plinkettreviews', 'url': link}, {'title': name})

elif mode == 'plinkettreviews':
    url = addon.queries['url']
    html = get_http_error(url)

    section = re.search('<h1 class="page-title">.+?</h1>(.+?)<script type="text/javascript">', html, re.DOTALL).group(1)
    match = re.compile('<a href="(.+?)"><img src="(.+?)">').findall(section)
    for link, thumb in match:
        name = re.search("[http://]*[a-z./-]*/(.+?)/",'/' + link).group(1).replace('-',' ').replace('/',' ').title()
        
        if re.search('http',link):
            newlink = link
        else:
            newlink = url + link
        addon.add_video_item({'url': newlink},{'title':name},img=thumb)

elif mode == 'halfbag':
    url = addon.queries['url']
    html = get_http_error(url)
    
    halfbag = re.search('<li id="menu-item-527"(.+?)</ul>', html, re.DOTALL)
    if halfbag:
        match = re.compile('<a href="(.+?)">(.+?)</a></li>').findall(halfbag.group(0))
        for link, name in match:
            addon.add_directory({'mode': 'halfbag-episodes', 'url': link}, {'title': name})


elif mode == 'halfbag-episodes':
    url = addon.queries['url']
    html = get_http_error(url)

    section = re.search('<h1 class="page-title">.+?</h1>(.+?)<script type="text/javascript">', html, re.DOTALL).group(1)
    match = re.compile('<a href="(http://[www.]*(redlettermedia|youtube)\.com/[a-zA-Z0-9-/_?=]*[/]*)"[ target=0]*><img src="(.+?jpg)"></a>', re.DOTALL).findall(section)
    for link, blank, thumb in match:
        episodenum = re.search('([0-9]+)[.]jpg', thumb)
        if episodenum:
            episode_name = 'Episode ' + str(episodenum.group(1))
        else:
            filename = re.search('[^/]+$', thumb).group(0)
            episode_name = re.search('(.+?)[.]jpg', filename).group(1).replace('_',' ').title()
        addon.add_video_item({'url': link},{'title': episode_name},img=thumb)
    
    shortmatch = re.compile('<a href="(http://www.youtube.com/.+?)" target=0><img src="(.+?)"></a>').findall(html)
    for link, thumb in shortmatch:
        filename = re.search('[^/]+$', thumb).group(0)
        episode_name = re.search('(.+?)[.]jpg', filename).group(1).replace('_',' ').title()
        addon.add_video_item({'url': link},{'title': episode_name},img=thumb)


elif mode == 'bestworst':
    url = addon.queries['url']
    html = get_http_error(url)

    section = re.search('<h1 class="page-title">.+?</h1>(.+?)<script type="text/javascript">', html, re.DOTALL).group(1)
    match = re.compile('<a href="(http://[www.]*(redlettermedia|youtube)\.com/[a-zA-Z0-9-/_?=]*[/]*)"[ target=0]*><img src="(.+?jpg)"></a>', re.DOTALL).findall(section)
    for link, blank, thumb in match:
        episodenum = re.search('([0-9.]+)\.jpg', thumb)
        if episodenum:
            episode_name = 'Episode ' + str(episodenum.group(1))
        else:
            filename = re.search('[^/]+$', thumb).group(0)
            episode_name = re.search('(.+?)[.]jpg', filename).group(1).replace('_',' ').title()
        addon.add_video_item({'url': link},{'title': episode_name},img=thumb)
    
    shortmatch = re.compile('<a href="(http://www.youtube.com/.+?)" target=0><img src="(.+?)"></a>').findall(html)
    for link, thumb in shortmatch:
        filename = re.search('[^/]+$', thumb).group(0)
        episode_name = re.search('(.+?)[.]jpg', filename).group(1).replace('_',' ').title()
        addon.add_video_item({'url': link},{'title': episode_name},img=thumb)


elif mode == 'featurefilms':
    url = addon.queries['url']
    html = get_http_error(url)
    
    r = re.search('FEATURE FILMS</a>.+?<ul class="sub-menu">(.+?)</ul>', html, re.DOTALL)
    if r:
        match = re.compile('<li.+?<a href="(.+?)">(.+?)</a></li>').findall(r.group(1))
    else:
        match = None
           
    thumb = re.compile('<td bgcolor="white" width=200><a href=".+?"><img src="(.+?)"></a></td>').findall(html)

    #Add each link found as a directory item
    i = 0
    for link, name in match:
        addon.add_video_item({'url': link}, {'title': name}, img=thumb[i])
        i += 1

elif mode == 'film':
    url = addon.queries['url']
    html = get_http_error(url)

    match = re.compile('<td><a href="(.+?)".*><img src="(.+?)".*>').findall(html)
    for link, thumb in match:
        link = url + link.replace(url,'')
        name = link.replace(url,'').replace('-',' ').replace('/',' ').title()
        addon.add_video_item({'url': link},{'title': name}, img=thumb)
   
elif mode == 'shortfilms':
    url = addon.queries['url']
    html = get_http_error(url)

    r = re.search('SHORTS AND WEB VIDEOS</a>.+?<ul class="sub-menu">(.+?)</ul>', html, re.DOTALL)
    if r:
        match = re.compile('<a href="(.+?)">(.+?)</a></li>').findall(r.group(1))
            
    # Add each link found as a directory item
    for link, name in match:
       addon.add_directory({'mode': 'shortseason', 'url': link}, {'title': name})

elif mode == 'shortseason':
    url = addon.queries['url']
    html = get_http_error(url)
    
    #Check if there are any videos embedded on the page
    if re.search('[<embed src=|youtube.com/embed]',html):
        addon.add_video_item({'url': url},{'title': 'Video'})
    else:
        match = re.compile('<td><a href="(.+?)".*><img src="(.+?)".*></a></td>').findall(html)
        
        # Add each link found as a video item
        for link, thumb in match:
            name = link.replace(url,'').replace('-',' ').replace('/',' ').title()
            link = url + link.replace(url,'')
            addon.add_video_item({'url': link},{'title': name},img=thumb)


if not play:
    addon.end_of_directory()