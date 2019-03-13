#!/usr/bin/python
# _*_ coding: utf-8 _*_

import sys, os, time, pypyodbc, json

def Now( Format="%d\%m\%Y %H:%M:%S" ):
    return time.strftime(Format, time.localtime() )

#base sur le connecteur natif
class SQLiteTools:
    import sqlite3
    def __init__( self, dbpath, AutoCommit=True ):
        self.AutoCommit = AutoCommit
        self.dbh = sqlite3.connect(dbpath, check_same_thread=False)
        self.dbh.row_factory = sqlite3.Row
        self.stmt = self.dbh.cursor()
        self.rowcount = 0

    def Query( self, querystr, listparam=[] ):
        self.rowcount = self.stmt.execute("%s;" % querystr, listparam).rowcount
        if querystr.strip().upper()[:6] != "SELECT" and self.AutoCommit:
            self.dbh.commit()

    def FetchAll(self):
        return self.stmt.fetchall()

    def Rollback(self):
        self.dbh.rollback()

    def Commit(self):
        self.dbh.commit()

    def Close( self ):
        self.dbh.close()

#classe mere pour Oracle/SQLS
class ODBCTools:
    def __init__( self ):
        self.driver  = ""
        self.dbh     = None
        self.sth     = None
        self.cur     = None
        self.params  = []
        self.count   = 0
        self.ddbport = None
        self.AutoCommit = True                   #db.AutoCommit = False pour modifier, True par défaut.

    #A SURCLASSER EN FONCTION DU DRIVER ODBC
    def Connect( self,                           #instance
                 dbhost,                         #serveur
                 dbname,                         #SID de la base
                 dbuser,                         #user pour la connexion
                 dbpass,                         #pwd pour la connexion
                 dbschema,                       #schema de la base, en general = dbuser
                 dbport ):                       #N� de port pour la connexion
        
        conn_string = "DRIVER={%s}; DBQ=%s; Uid=%s; Pwd=%s;" % ( self.driver, dbname, dbuser, dbpass )
        self.dbh = pypyodbc.connect(conn_string)

    def Query( self, querystr, params=[] ):
        self.count = 0
        self.cur    = self.dbh.cursor()
        self.cur.execute( querystr, params )
        if not ( querystr.strip().upper()[:6] != "SELECT" ):
            self.count = self.cur.rowcount
            if self.AutoCommit:
                self.Commit()

    def FetchAll( self ):
        #self.cur.execute( self.qry, self.params )
        columns = [column[0].lower() for column in self.cur.description]

        for row in self.cur.fetchall():
            self.count+=1
            yield dict(zip(columns, row))

    def GetRowCount( self ):
        return self.count

    def Commit( self ):
        self.cur.commit()

    def Rollback( self ):
        self.cur.rollback()

    def Close( self ):
        self.cur.close()
        self.dbh.close()

#classe OracleTools hérite de ODBCTools
class OracleTools(ODBCTools):
    def __init__( self ):
        ODBCTools.__init__( self )
        self.driver  = 'Oracle dans OraClient11g_home1'

    def Connect( self,                           #instance
                 dbname,                         #SID de la base
                 dbuser,                         #user pour la connexion
                 dbpass ):                       #N° de port pour la connexion
        
        conn_string = "DRIVER={%s}; DBQ=%s; Uid=%s; Pwd=%s;" % ( self.driver, dbname, dbuser, dbpass )
        self.dbh = pypyodbc.connect(conn_string)

#classe SQLServerTools herite de ODBCTools
class SQLServerTools(ODBCTools):
    def __init__( self ):
        ODBCTools.__init__( self )
        self.driver  = 'SQL Server'

    def Connect( self,                           #instance
                 dbhost,                         #adresse du serveur
                 dbname,                         #SID de la base
                 dbuser,                         #user pour la connexion
                 dbpass ):                       #N� de port pour la connexion
        
        conn_string = "DRIVER={%s};Server=%s;Database=%s;Uid=%s;Pwd=%s;" % ( self.driver, dbhost, dbname, dbuser, dbpass )
        self.dbh = pypyodbc.connect(conn_string)

#comptes rendus d'execution
class LogTools:
    def __init__( self, fileName, msgFile ):
        self.fileName = fileName

        fh= open( self.fileName, 'ab' )
        fh.write( "%s\t*** INITIALISATION DU FICHIER LOG ***\n" % Now() )
        fh.close()

        self.MSG = {}
        try:
            fh = open( msgFile, "rb")
            for line in fh:
                test = line.split( "=" )
                if test>=2:
                    cle = test[0]
                    rem = len(cle)+1
                    val = line.replace( "\r", "" ).replace( "\n", "" )[ rem: ]
                self.MSG[cle] = val
        except:
            print "aucun fichier message ! "
            pass

    def write( self, level, command, params=[] ):
        fh= open( self.fileName, 'ab' )
        if self.MSG.has_key( command ):
            fh.write( "[%s]\t%s\t%s\t%s\n" % ( Now(), level, self.MSG[command], params ) )
        else:
            fh.write(  "%s\t%s\tcommande inconnue : %s\n" % ( Now(), level, command ) )
        fh.close()

#recuperer des parametres depuis un fichier de conf simple
class ConfTools:
    def __init__( self, Fichier, Verbose=True ):
        self.Cfg = {}
        self.CfgOrder = {}
        self.commentaires = {}
        fh = open( Fichier, "rb" )
        nline = 0
        for line in fh:
            nline+=1
            l = line.replace( "\r", "" ).replace( "\n", "" )
            if l.find( "=" )>=0 and not l.strip().find( "#" )==0:
                cle = l.split( "=" )[0]
                val = l[ len(cle): ]
                self.Cfg[ cle.strip() ] = val.strip()
                self.CfgOrder[nline] = cle.strip()
            else:
                self.commentaires[nline] = "%s\n" % l
        fh.close()
        self.Max = nline

    def rewrite( self ):
        fw = open( Fichier, "wb" )

        for i in range( 1, self.Max ):
            if Verbose:
                print "reecriture ligne ", i

            if self.CfgOrder.has_key( i ):
                cle = self.CfgOrder[i]
                val = self.Cfg[cle]
                fw.write( "%s=%s\n" % (cle, val) )

            elif self.commentaires.has_key( i ):
                fw.write( "%s\n" % self.commentaires[i] )

            else:
                fw.write( "\n" )

        fw.close()

    def get( self, cle ):
        if self.Cfg.has_key( cle ):
            return self.Cfg[cle]
        else:
            if Verbose:
                print "paramètre inconnu : %s" % cle
            return ""

    def set( self, cle, val ):
        self.Max = self.Max+1
        self.Cfg[ cle ] = val
        self.CfgOrder[ self.Max ] = cle
        self.rewrite()

#gestion de requetes sous forme fichiers text/sql dans rep dedie
class QueryHandler:
    def __init__( self, usrpath="" ):
        self.defaultPath = r"./sql"
        if usrpath:
            self.defaultPath=usrpath

        if not os.path.isdir( self.defaultPath ):
            print "ABSENCE DU REPERTOIRE REQUETES"
            sys.exit(90001)

    def GetQuery( self, qryName ):
        if os.path.isfile( os.path.join( self.defaultPath, qryName+".sql" ) ):
            fh = open( os.path.join( self.defaultPath, qryName+".sql" ), "rb" )
            txt = fh.read()
            fh.close()
            return txt
        return False
    
    def Count( self ):
        import glob, re
        queryFiles = [f for f in glob.glob(os.path.join(self.defaultPath, '*')) if re.match('^.*\.sql$', f, flags=re.IGNORECASE)]
        return len( queryFiles )
    
    def ShowAvailable( self ):
        import glob, re 
        print "*" * 50
        print "Affichage des requetes du programme"
        print "*" * 50
        count = 0
        for queryFile in [f for f in glob.glob(os.path.join(self.defaultPath, '*')) if re.match('^.*\.sql$', f, flags=re.IGNORECASE)]:
            count+=1
            queryFileName = os.path.basename(queryFile)
            print u"%s\tGetQuery -->  %s " % ( count, os.path.splitext(queryFileName)[0] )
        print "*" * 50
        print "%s requetes disponibles" % count
        print "*" * 50
        return

#compteur de temps d'execution entre 2 actions
class Chrono:    
    def __init__( self ):
        self._start = None
        self._stop  = None
        self._interval = None

    def start( self ):
        self._interval = None
        self._start = time.time()

    def stop( self ):
        self._stop = time.time()

    def delta( self ):
        self._interval = self._stop - self._start
        self.start = None
        return round( self._interval, 2 )

#gestion de hashtables hérité de dict avec outils de conversion
class hashmap(dict):
    def __init__(self, *arg, **kw):
        super(dict, self).__init__(*arg, **kw)
        if len(arg)>0 and isinstance(arg[0], dict):
            for i in arg[0]:
                self[i] = arg[0][i]
    def to_json(self):
        return json.dumps(self, sort_keys=True, indent=4, separators=(',', ': '))
    def to_xml(self, customroot=""):
        return dict2xml(self, customroot).output
    def has_value(self, val):
        for key in self:
            if self[key]==val:
                return key
        return False

#conversion hashmap/xml. ajouter: valeur liste
class dict2xml:
    def __init__(self, d, customroot=""):
        self.d = d 
        self.indent = 0
        self.esc = hashmap({ '"':"&quot;",
                             "'": "&apos;",
                             "<": "&lt;",
                             ">": "&gt;",
                             "&": "&amp;" })
        self.output = self.prolog( "xml", hashmap({ "version":"1.0", "encoding":"UTF-8" }))
        self.customroot = customroot
        if self.customroot:
            self.output+= self.tagopen(customroot)
        self.work( self.d )
    
    def escape(self, _str):
        for i in self.esc:
            _str = _str.replace( i, self.esc[i] )
        return _str
    
    def prolog(self, tag, dargval={}):
        argval=" "
        for i in dargval:
            argval+="%s=\"%s\" " % ( i, self.escape( dargval[i]))
        argval = argval[:-1]

        ret = "<?%s%s ?>\n" % (tag, argval)
        
        self.indent+=4
        return ret


    def tagopen(self, tag, dargval={}):
        argval=" "
        for i in dargval:
            argval+="%s=\"%s\" " % ( i, self.escape( dargval[i]))
        argval = argval[:-1]

        ret = "%s<%s%s>\n" % ((" "*self.indent), tag, argval)
        
        self.indent+=4
        return ret

    def tagclose(self, tag): 
        self.indent-=4
        ret = "%s</%s>\n" % ((" "*self.indent), tag)
        return ret

    def emptytag( self, tag, dargval={}):
        argval=" "
        for i in dargval:
            argval+="%s=\"%s\" " % ( i, self.escape( dargval[i]))
        argval = argval[:-1]
        return "%s<%s%s />\n" % ((" "*self.indent), tag, argval)

    def work( self, d, keyclose="" ):
        for item in d:
            key = item
            val = d[item]
            if isinstance( val, dict ):
                self.output+=self.tagopen( key )
                self.work( val, key )
            else:
                if val:
                    if isinstance(val, list):
                        for ins in val:
                            self.output+= self.tagopen( key )
                            self.output+= "%s%s\n"% ((" "*self.indent), self.escape(ins))
                            self.output+= self.tagclose( key )
                    else:
                        self.output+= self.tagopen( key )
                        self.output+= "%s%s\n"% ((" "*self.indent), self.escape(val))
                        self.output+= self.tagclose( key )
                else:
                    self.output+= self.emptytag( key )
        
        if keyclose:
            self.output+= self.tagclose( keyclose )
        
        #fin de parcours du dictionnaire principal
        if d == self.d:
            if self.customroot:
                self.output+= self.tagclose( self.customroot )
            self.output+= self.tagclose( "xml" )
