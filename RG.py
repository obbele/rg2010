#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
# Copyright 2010 John Obbele <john.obbele@gmail.com>
#
#                DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#                        Version 2, December 2004
#
# Copyright (C) 2004
# Sam Hocevar 14 rue de Plaisance, 75014 Paris, France
# Everyone is permitted to copy and distribute verbatim or modified
# copies of this license document, and changing it is allowed as long as
# the name is changed.
#
#                 DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#     TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION
#
#     0. You just DO WHAT THE FUCK YOU WANT TO.

                   === Python Player for Roland-Garos ===

- retrieve JSON and extract from it the list of mms flux
- parse website mainpage and extract from it the list of current matches
- provide a CLI interface as a proof of concept (see cli())
- provide a PyGTK interface for lazy men (see class MainWindow)

The function LAUNCH_EXTERNAL_PLAYER (url) try to guess your preferred
video player for mms/wmv flux, if it's not working, you will have to
hack it yourself.
"""

import json
import urllib, BeautifulSoup
import os, os.path

OFFLINE=False

def LAUNCH_EXTERNAL_PLAYER( url):
    """ FIXME: hack your video player here ! """
    print "Processing:", url

    if OFFLINE : return

    if os.path.exists( "/usr/bin/mplayer" ):
        bin = "/usr/bin/mplayer"
    elif os.path.exists( "/usr/bin/parole" ):
        bin = "/usr/bin/parole"
    elif os.path.exists( "/usr/bin/dragon" ):
        bin = "/usr/bin/dragon"
    elif os.path.exists( "/usr/bin/totem" ):
        bin = "/usr/bin/totem"

    os.spawnlp(os.P_NOWAIT, bin, bin, url)

if OFFLINE :
    HOME_PAGE="page_blank.html"
    TOKEN="token.txt"
    WMV_JSON="wmv.json"
else :
    HOME_PAGE="http://roland-garros.sport.francetv.fr/video-direct"
    TOKEN="http://roland-garros.sport.francetv.fr/appftv/akamai/token/gentoken1.php?flux=roland_%s_%s"
    WMV_JSON="http://roland-garros.sport.francetv.fr/sites/www.sport/themes/roland-garros/php/direct/getListVideo.php?player=WMV"

# javascript file describing managing the authentication process
# keep this for reference
JSOURCE="http://roland-garros.sport.francetv.fr/sites/sport.francetv.fr/themes/roland-garros/js/direct-min.js"

def _wget(url) :
    """ get data from an url and return raw text """
    response = urllib.urlopen(url)
    return response.read()

class Crawler():
    """ Using BeautifulSoup, parse the HTML page
    and map idFlux versus match information

    You can retrieve current information throught self.matches
    You can refresh the match list with self.refresh()
    """
    def __init__(self):
        self.refresh()

    def refresh(self) :
        """ Refresh the dictionary 'matchID' => match
        """
        self.matches = {}

        data = _wget(HOME_PAGE)
        soup = BeautifulSoup.BeautifulSoup(data)
        for div in soup.findAll("div", {"class":"JeuParJeu"}) :

            try :
                id,match = self._parseMatch( div)
                self.matches[id] = match
            except AttributeError:
                pass
                #print "Error when parsing", div

    def _parseMatch(self, div) :
        """
        <div class="JeuParJeu" id="match3">
        <h3>Court 1</h3>
        <p class="duree">Dur&eacute;e 1h20</p>
        <div class="equipe1"> <img
        src="http://medias.francetv.fr/STATIC/salma/images/flag/png/GBR.png"
        class="png" alt="" border="0" /> A.MURRAY (4)</div>
        <div class="equipe2"> <img
        src="http://medias.francetv.fr/STATIC/salma/images/flag/png/ARG.png"
        class="png" alt="" border="0" /> J.CHELA</div>
        <div class="equipe1-balle"></div>
        <div class="equipe2-balle"><img
        src="/sites/www.sport/themes/roland-garros/img/balle.png" class="png"
        alt="" border="0" /></div>
        <div class="equipe1-score"><span>6</span> 3   </div>
        <div class="equipe2-score">2 3   </div>
        <a href="?idFlux=3"><span>Voir le match</span></a>
        </div>
        """
        match = {}

        match['name'] = div.attrMap['id']

        equipe1 = []
        for p in div.findAll("div", {"class":"equipe1"}) :
            equipe1 += p.text
        match['players1'] = "".join(equipe1)

        equipe2 = []
        for p in div.findAll("div", {"class":"equipe2"}) :
            equipe2 += p.text
        match['players2'] = "".join(equipe2)

        score1 = div.find("div" , {"class":"equipe1-score"})
        match['score1'] = score1.text.replace(" ", "")
        score2 = div.find("div" , {"class":"equipe2-score"})
        match['score2'] = score2.text.replace(" ", "")

        idFlux = div.find('a').attrs[0][1]
        idFlux = idFlux[len('?idFlux='):] # strip '?idFlux='

        return idFlux, match

class AkamaiPlayer():
    """ Retrieve the list of WMVs flux
    and manage authentication tokens

    You can retrieve information throught self.list() or self.videos
    You can retrieve refresh the list with self.refresh()
    """
    def __init__(self, quality="SQ"):
        self.changeQuality(quality)
        self.refresh()

    def changeQuality(self, quality):
        if quality == "SQ" or quality == "HQ" :
            self.quality = quality
        else :
            raise Exception("quality should be either 'SQ' or 'HQ'")

    def get(self, id):
        """ Given video ID, return its url,
        including authentication token
        """

        id = str(id) # force str object

        identifier = id + "_" + self.quality

        try :
            return self._akamaiToken( self.videos[identifier]
                                    , id
                                    , self.quality)
        except KeyError:
            print "Error: unknown key"
            print " available videos: ", ", ".join(self.videos.keys())


    def list(self):
        """ Return the list of available videos """
        keys = self.videos.keys()
        for i,k in enumerate(keys):
            keys[i] = k[0:-3] # skip last 3 chars ("_{S,H}Q")
        return keys

    def refresh(self):
        """ Return a dictionary similar to js's itemListSL
        each element is a simple association "flux" -> "url"
        where flux looks like "1_HQ"
        """
        raw_data = _wget(WMV_JSON)
        data = json.loads( raw_data)

        itemListSL = {}

        for e in data['videos'] :
            if e['url_HQ'] == "smooth" :
                raise NotImplementedError
            else :
                id = e['idMatch']
                itemListSL[id + "_SQ"] = e['url_SQ']
                itemListSL[id + "_HQ"] = e['url_HQ']

        self.videos = itemListSL


    """ JAVASCRIPT decypher
    function decryptToken(a) {
        return (a + "").replace(/[A-Za-z]/g, function (b) {
            return String.fromCharCode((((b = b.charCodeAt(0)) & 223) - 52) % 26 + (b & 32) + 65)
        })
    }
    """
    def _decryptToken(self, id):
        l = list(id)
        for i,k in enumerate(l) :
            if  k.isalpha() :
                b = ord(k)
                l[i] = chr(((b & 223) - 52) % 26 + (b & 32) + 65)
        return "".join(l)


    """ JAVASCRIPT token
    function isActiveToken(a) {
        return /\?aifp=/i.test(a)
    }
    function akamaiToken(e, b, d) {
        var a = isActiveToken(e);
        if (a) {
            if (b == "8") {
                b = "6"
            }
            if (b == "9") {
                b = "7"
            }
            var c = $.ajax({
                url: "/appftv/akamai/token/gentoken1.php?flux=roland_" + b + "_" + d,
                async: false
            }).responseText;
            c = decryptToken(c);
            e = e + "&auth=" + c
        }
        return e
    }
    ...
    akamaiToken(b.src, idMatch, qualityDirect)
      where b.src = "mms://.../e_rg_2010_7l.wsx?aifp=v052"
            idMath = 1 | 2 | 3 | ...
            qualityDirect = "SQ" | "HQ"

    """
    def _akamaiToken(self, url, id, quality):
        e,b,d = url, id, quality

        #FIXME: check if the token is active

        if (b == "8") :
            b = "6"
        if (b == "9") :
            b = "7"

        if OFFLINE : raw_hash = _wget( TOKEN )
        else       : raw_hash = _wget( TOKEN % (id, quality) )

        c = decrypted_hash = self._decryptToken(raw_hash)

        return e + "&auth=" + c

    def _create_asx(self):
        """ WARNING: function not working
        Should properly encode XML entities ('&' => '&amp;')
        USE AT YOUR OWN RISKS
        """

        raise NotImplementedError

        head = """<ASX VERSION = \"3.0\">
        <TITLE>Title</TITLE>
        """
        tail = "</ASX>"

        ENTRY = """
        <ENTRY>
        <TITLE>%s</TITLE>
        <REF HREF = \"%s\" />
        </ENTRY>
        """
        r = head
        for identifierk,url in self.videos.iteritems() :
            id = identifierk[0]
            quality = identifierk[-2:]
            try :
                url = akamaiToken(url, id, quality)
                r += ENTRY % (identifierk, url)
            except :
                print "Error: ignoring", url
        r += tail

        return r

class LOLO():
    """ Tie a crawler and a player together
    """
    def __init__(self,quality="SQ"):
        self.crawler = Crawler()
        self.player = AkamaiPlayer(quality)
        self.list = self.crawler.matches

    def refresh(self):
        """ Refresh both the player and the crawler component
        """
        self.crawler.refresh()
        self.player.refresh()

    def get(self, id):
        """ Given a flux ID, return the URL, 
        including a authentication token
        """
        return self.player.get(id)

    def __str__(self):
        """ Internal function invoked when calling "print"
        """
        s = ""
        for i,v in self.crawler.matches.iteritems() :
            s += "Id:" + i + "\n"
            s += "\tjoueur(s) 1: " + v['players1'] + "\n"
            s += "\tjoueur(s) 2: " + v['players2'] + "\n"
            s += "\t" + v['score1'] + "\n"
            s += "\t" + v['score2'] + "\n"
            s += "\n"
        return s

def cli():
    """ A simple Read-eval-print loop (REPL) for selecting a match
    and launching the video player.
    """
    print "Testing flying dog"
    print "quality ?(SQ|HQ)"
    q = raw_input()
    client = LOLO(q)

    print "available matches:"
    print client

    end = False
    while not end :
        print "choice ? (q=exit, r=refresh, x=play match number x)"
        r = raw_input()
        if r == "q" :
            end = True
        elif r == "r" :
            client.refresh()
            print client
            continue
        else :
            url = client.get(r)
            LAUNCH_EXTERNAL_PLAYER( url)

###
### GTK stuff
###

import pygtk
pygtk.require('2.0')
import gtk  

class MainWindow(LOLO):
    """Adapted from the PyGTK tutorial, chapter 2
    """
    def __init__(self,quality="HQ"):
        LOLO.__init__(self, quality)
        self._init_gtk()
        self.refresh()

    def refresh(self):
        LOLO.refresh(self)
        self._refresh_list_store()

    def _refresh_list_store(self) :
        self.liststore.clear()

        for id,match in self.crawler.matches.iteritems():
            score = match['score1'] + "\n" + match['score2']
            players = match['players1'] + "\n" + match['players2']
            self.liststore.append( [int(id), score, players ])

        self.liststore.set_sort_column_id( 0, gtk.SORT_ASCENDING)

    def _init_gtk(self):
        """Create the GTK widgets
        """
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_title('Roland Garros 2010')
        window.set_size_request(300, 400)
        window.show()

        window.connect('delete_event', self.quit)

        window.set_border_width(10)

        vbox = gtk.VBox()
        window.add( vbox)

        label = gtk.Label("¡ Pirater TUE des chatons !")
        vbox.pack_start( label, expand=False, fill=False)

        liststore = gtk.ListStore(int,str,str)

        listview = gtk.TreeView( liststore)
        vbox.pack_start( listview)

        #Creating ID column
        #
        column = gtk.TreeViewColumn('ID')
        listview.append_column( column)

        cell = gtk.CellRendererText()
        column.pack_start( cell, True)
        column.add_attribute( cell, 'text', 0)
        column.set_sort_column_id(0)
        listview.set_search_column( 0)

        #Creating score column
        #
        column = gtk.TreeViewColumn('Score')
        listview.append_column( column)

        cell = gtk.CellRendererText()
        column.pack_start( cell, True)
        column.add_attribute( cell, 'text', 1)

        #Creating players column
        #
        column = gtk.TreeViewColumn('Joueurs')
        listview.append_column( column)

        cell = gtk.CellRendererText()
        column.pack_start( cell, True)
        column.add_attribute( cell, 'text', 2)

        #Qualitay box
        qualitystore = gtk.ListStore(str)
        combobox = gtk.ComboBox(qualitystore)
        cell = gtk.CellRendererText()
        cell.set_property( 'xalign', 0.5)
        combobox.pack_start(cell, True)
        combobox.add_attribute(cell, 'text', 0)

        combobox.append_text("SQ")
        combobox.append_text("HQ")
        if self.player.quality == "SQ" :
            combobox.set_active(0)
        else :
            combobox.set_active(1)
        def on_quality_box__changed( combobox):
            model = combobox.get_model()
            active = combobox.get_active()
            if active < 0 : return
            value = model[active][0]
            self.player.changeQuality( value)
        combobox.connect( "changed", on_quality_box__changed)
        vbox.pack_start( combobox, expand=False, fill=False)

        #Buttonbox
        buttonbox = gtk.HBox()
        vbox.pack_end( buttonbox, expand=False, fill=True)

        button = gtk.Button("_Refresh", gtk.STOCK_REFRESH)
        def on_refresh__clicked( button) :
            self.refresh()
        button.connect( "clicked", on_refresh__clicked)
        buttonbox.pack_start( button, expand=True, fill=True)

        button = gtk.Button("_Quit", gtk.STOCK_QUIT)
        button.connect( "clicked", self.quit)
        buttonbox.pack_start( button, expand=True, fill=True)

        def on_listview__row_activated(tv, path, view_column=None) :
            """ Trigger when a row is doubled-clicked or 
            Ctrl+Space is pressed
            """
            iter = liststore.get_iter( path)
            id = liststore.get_value( iter, 0)
            url = self.get( id)
            LAUNCH_EXTERNAL_PLAYER( url)
        listview.connect( "row-activated", on_listview__row_activated)

        window.show_all()

        #Keep at hand
        self.liststore = liststore

    def quit(self, widget, data=None):
        """ End GTK main loop
        and thus terminate the program
        """
        print "ByeBye !"
        gtk.main_quit()

def launch_gtk():
    """ Guess it ?
    """
    widget = MainWindow()
    gtk.main()

if __name__ == '__main__':
    #cli()
    launch_gtk()

# vim:textwidth=72:
