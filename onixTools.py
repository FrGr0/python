#!/bin/lastpython
# _*_ coding: ISO-8859-15 _*_
##########################################################################################################################
# auteur  : François Gros
# datmaj  : 04/12/2012
# version : 1.4
# notes   : adaptation aux formats ONIX 2.1 et 3.0 
#           détection automatique du format et de la référence 12/04/2013
#           harmonisation du flux obtenu en sortie
##########################################################################################################################


import time, sys, shutil, os, re 
import xml.etree.ElementTree as etree
from HTMLParser import HTMLParser       
        
##########################################################################################################################

#strip les balises html
def no_html(data):    
    x = re.compile( re.escape( '<br' ), re.IGNORECASE )
    data = x.sub( '\r\n<br', data )
    
    p = re.compile(r'<.*?>')
    return p.sub('', data)
    
    
    
#remplace tous les caractères d'échappement html type "&nbsp;" "&#255;"
def unescape( s ):
    s = HTMLParser.unescape.__func__(HTMLParser, s)
    return s    
   

#plusieurs verifications de problèmes d'encodage...
#caractères ayant un code inferieur à 13 (sauf 10), remplacement de caractères unicode...
#retourne une chaine unicode sensée être "propre".
def Decode( s ):   

    if not s:
        s = ''
        
    s = unescape( s )
    s = no_html( s )
    
    I = len( s ) - 1
    L = 0
    while I > 0:
      C = ord( s[I] )
      if C < 32 and C != 10:
        IsLow  = C != 13
        L     += 1
        s    = s[:I] + s[I+1:]
      I -= 1      
        
    try:
      s = s.decode( 'UTF-8', 'replace' )
    except:
      pass
    
    try:
      s = s.decode( 'ISO-8859-15', 'replace' )
    except:
      pass    
      
      
    # 02/05/11 Certaines chaînes contiennent des caractères dont le
    # code est inférieure à 32 (espace) outre le code 10
    # L'idée et de supprimer ces caractères impropres    
    
    s = s.replace( u'\u2019', u"'" )     
    s = s.replace( u'\u0152', u"Oe" )
    s = s.replace( u'\u0153', u"oe" )
    s = s.replace( u'\u2026', u"..." ) 
    s = s.replace( u'\u2014', u'' )    
    s = s.replace( u'\u2013', u'' )    
    s = s.replace( u'\u2022', u'*' )    
    s = s.replace( u'\u2028', u'\r\n' )    
    s = s.replace( u'\u20ac', u'Euros' )        
    s = s.replace( u'\u201c', u'"' )     
    s = s.replace( u'\u201d', u'"' ) 

    #double une simple quote pour l'integration SQL
    s = s.replace( "'", "''" )
    
    return s


##########################################################################################################################
##scan les fichiers XML et alimentation du dictionnaire passé en 1er argument (pour pouvoir le rendre incrémental)
class ParseOnix():
    
    def __init__( self, file ):
                
        #dictionnaire product vide. 1 par element product 
        #aucun doublon possible, la clé étant l'objet "Product"
        self.REFS = {}
        self.DefaultDico =  { 'gencod'       : '', 
                              'titre'        : '',
                              'auteur'       : '', 
                              'biographie'   : '', 
                              'presentation' : '', 
                              'collection'   : '',
                              'numcollection': '',
                              'prix'         : '0', 
                              'tauxtva'      : '5.5',
                              'prixht'       : '0',
                              'dispo'        : '6',
                              'nbpages'      : '0', 
                              'hauteur'      : '0', 
                              'largeur'      : '0', 
                              'epaisseur'    : '0',
                              'poids'        : '0',
                              'image'        : '',
                              'editeur'      : '',
                              'distributeur' : '',
                              'dateparution' : '01/01/2070',
                              'pays'         : '',
                              'language'     : '',
                              'support'      : ''
                            }

        self.handle  = open( file, "rb" )
        tree         = etree.parse( self.handle )    
        self.Root    = tree.getroot()  
        
        
        if self.Root.attrib.has_key( 'release' ):
            self.Release = self.Root.attrib[ 'release' ]
            
        else:           
            self.Release = '2.1'
                
        
        #récuperation du schemaLocation
        SchemaLocation = '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'
                
        if self.Root.attrib.has_key( SchemaLocation ):
            self.ref = '{%s}' % self.Root.attrib[ SchemaLocation ].split( ' ' )[0]
            
        
        elif re.findall( '{.*}', self.Root.tag ):
            self.ref = re.findall( '{.*}', self.Root.tag )[0]           
        
        else:
            self.ref = ''                            
        
        
        return
                         
        
    def GetValue( self, node, o_tag_to_match, o_id_to_match='', value_to_match='', o_field_name='', default='' ):
        
        tag_to_match = self.ref+o_tag_to_match
        id_to_match  = self.ref+o_id_to_match
        field_name   = self.ref+o_field_name
        
        for ProdElem in node:
            n = 0
            d = {}
            contenu = {}
            if ProdElem.tag==tag_to_match:         
                
                if not o_id_to_match:
                    try:
                        if ProdElem.text.split():
                            ProdElem = ProdElem.text
                    except:
                        pass
                        
                    return ProdElem
                              
            
                for ProdIdent in ProdElem:                                                            
                    if not d.has_key(n):
                        d[n] = contenu                    
                    contenu[ ProdIdent.tag ] = ProdIdent.text
                    d[n] = contenu                
                n+=1            
                
                list_to_match = value_to_match.split( '§' )
                
                for item in d:
                    if ( d[item].has_key( field_name ) and 
                         d[item].has_key( id_to_match ) ):                         
                        #if d[item][ id_to_match ] == value_to_match:
                        if d[item][ id_to_match ] in list_to_match:
                            try:
                                if eval( d[item][ field_name ] ) == 0:
                                    d[item][ field_name ] = default
                            except:
                                pass       
                            return d[item][ field_name ]
                        
        return default
    
    
    def WorkFile( self ):
    
        #liste des codes dispos
        CodesDispo = { '10': '2',
                       '11': '3',
                       '12': '2', 
                       '20': '1', 
                       '21': '1', 
                       '22': '1',
                       '23': '1' }
        
        #ici uniquement codes dispo a paraitre
        #si la clé n'existe pas : indispo (6)
            
        #compteur
        c     = 0
               
        ProdList = self.Root.findall( '%sProduct' % self.ref )                                            
        
        for Product in ProdList:
            
            #on initialise le dico Product à l'interieur du dico REFS
            self.REFS[ Product ]    = self.DefaultDico                                                                       
            
            ##########################################################################################################################
            #Format ONIX 2.1            
            if self.Release == '2.1':                                                          
                
                #elements XML
                _SupplyDetail           = self.GetValue( Product, 'SupplyDetail' )
                _Series                 = self.GetValue( Product, 'Series' )
                            
                #elements textes
                gencod                  = self.GetValue( Product, 'ProductIdentifier', 'ProductIDType', '15§03', 'IDValue' )            
                titre                   = self.GetValue( Product, 'Title', 'TitleType', '01', 'TitleText' )            
                auteur_principal_prenom = self.GetValue( Product, 'Contributor', 'ContributorRole', 'A01§B05', 'NamesBeforeKey' )
                auteur_principal_nom    = self.GetValue( Product, 'Contributor', 'ContributorRole', 'A01§B05', 'KeyNames' )
                biographie              = self.GetValue( Product, 'Contributor', 'ContributorRole', 'A01§B05', 'BiographicalNote' )            
                presentation            = self.GetValue( Product, 'OtherText', 'TextTypeCode', '01', 'Text' )
                collection              = self.GetValue( _Series, 'TitleOfSeries' )
                numerocollection        = self.GetValue( _Series, 'NumberWithinSeries', '', '' ,'', 0 )
                support                 = self.GetValue( Product, "ProductForm" )
                prix                    = self.GetValue( _SupplyDetail, 'Price', 'PriceTypeCode', '04§02', 'PriceAmount', 0 )
                tauxtva                 = self.GetValue( _SupplyDetail, 'Price', 'PriceTypeCode', '04§02', 'TaxRatePercent1', '5.5' )
                prixht                  = self.GetValue( _SupplyDetail, 'Price', 'PriceTypeCode', '04§02', 'TaxableAmount1', 0 )
                dispo_onix              = self.GetValue( _SupplyDetail, 'ProductAvailability' )     
                distributeur            = self.GetValue( _SupplyDetail, 'SupplierName' )
                nbpages                 = self.GetValue( Product, 'NumberOfPages', '', '', '', 0 )            
                hauteur                 = self.GetValue( Product, 'Measure', 'MeasureTypeCode', '01', 'Measurement', 0 )
                largeur                 = self.GetValue( Product, 'Measure', 'MeasureTypeCode', '02', 'Measurement', 0 )
                epaisseur               = self.GetValue( Product, 'Measure', 'MeasureTypeCode', '03', 'Measurement', 0 )
                poids                   = self.GetValue( Product, 'Measure', 'MeasureTypeCode', '08', 'Measurement', 0 )
                image                   = self.GetValue( Product, 'MediaFile', 'MediaFileTypeCode', '02§04§06', 'MediaFileLink' )
                editeur                 = self.GetValue( Product, 'Publisher', 'PublishingRole', '01', 'PublisherName' ) 
                dateparution            = self.GetValue( Product, 'PublicationDate' )
                pays                    = self.GetValue( Product, 'CountryOfPublication' )
                language                = self.GetValue( Product, 'Language', 'LanguageRole', '01§02', 'LanguageCode' )
                
                
                ##########################################################################################################################
                #infos alternatives ######################################################################################################                             
                
                if not editeur:
                    editeur                 = self.GetValue( Product, 'Imprint', 'NameCodeType', '06§02§01', 'ImprintName' )           
                
                if not auteur_principal_nom:
                    auteur_principal_nom    = self.GetValue( Product, 'Contributor', 'ContributorRole', 'A01§B05', 'PersonNameInverted' )
               
                
                ##########################################################################################################################           
                #traitements spéciaux ####################################################################################################
                if  auteur_principal_prenom:
                    auteur_principal_prenom = ', '+auteur_principal_prenom
                                    
                auteur = ''
                try:
                    auteur = Decode( auteur_principal_nom + auteur_principal_prenom )
                except:
                    print sys.exc_info()                    
                    pass   
                
                
                if dateparution:
                    dateparution = time.strftime( '%m/%d/%Y', time.strptime( dateparution, '%Y%m%d'  ) )                
                    
                dispo_medialivre   = 6
                #si le code onix est connu dans le dictionnaire des CodesDispo on recupere la valeur du dico #############################
                if CodesDispo.has_key( dispo_onix ):
                    dispo_medialivre = CodesDispo[ dispo_onix ]    
                                                                 

            ################################################################################################################################
            #format ONIX 3.0 !
            elif self.Release == '3.0':
            
                #recuperation des elements XML            
                _DescriptiveDetail      = self.GetValue( Product, 'DescriptiveDetail' )
                _CollateralDetail       = self.GetValue( Product, 'CollateralDetail' )
                _SupportingResource     = self.GetValue( _CollateralDetail, 'SupportingResource' )
                _ContentDetail          = self.GetValue( Product, 'ContentDetail' )
                _ContentItem            = self.GetValue( _ContentDetail, 'ContentItem' )            
                _TextItem               = self.GetValue( _ContentItem, 'TextItem' )
                _PublishingDetail       = self.GetValue( Product, 'PublishingDetail' )
                _ProductSupply          = self.GetValue( Product, 'ProductSupply' )
                _SupplyDetail           = self.GetValue( _ProductSupply, 'SupplyDetail' )
                _Prix                   = self.GetValue( _SupplyDetail, 'Price' )            
                _TitleDetail            = self.GetValue( _DescriptiveDetail, 'TitleDetail' )                     
                
                #recuperation des données textes
                gencod                  = self.GetValue( Product, 'ProductIdentifier', 'ProductIDType', '15§03', 'IDValue' )   
                support                 = self.GetValue( _DescriptiveDetail, 'ProductForm' )
                auteur_principal_prenom = self.GetValue( _DescriptiveDetail, 'Contributor', 'ContributorRole', 'A01§B05', 'NamesBeforeKey' )
                auteur_principal_nom    = self.GetValue( _DescriptiveDetail, 'Contributor', 'ContributorRole', 'A01§B05', 'KeyNames' )                    
                biographie              = self.GetValue( _DescriptiveDetail, 'Contributor', 'ContributorRole', 'A01§B05', 'BiographicalNote' )
                hauteur                 = self.GetValue( _DescriptiveDetail, 'Measure', 'MeasureType', '01', 'Measurement', 0 )
                largeur                 = self.GetValue( _DescriptiveDetail, 'Measure', 'MeasureType', '02', 'Measurement', 0 )
                epaisseur               = self.GetValue( _DescriptiveDetail, 'Measure', 'MeasureType', '03', 'Measurement', 0 )            
                poids                   = self.GetValue( _DescriptiveDetail, 'Measure', 'MeasureType', '08', 'Measurement', 0 )                                   
                presentation            = self.GetValue( _CollateralDetail, 'TextContent', 'TextType', '03', 'Text' )
                image                   = self.GetValue( _SupportingResource, 'ResourceVersion',  'ResourceForm', '02§04§06', 'ResourceLink' )
                nbpages                 = self.GetValue( _TextItem, 'NumberOfPages', '', '', '', 0 )
                editeur                 = self.GetValue( _PublishingDetail, 'Publisher', 'PublishingRole', '01', 'PublisherName' )
                dateparution            = self.GetValue( _PublishingDetail, 'PublishingDate', 'PublishingDateRole', '01', 'Date' )
                prix                    = self.GetValue( _SupplyDetail, 'Price', 'PriceType', '04§02', 'PriceAmount', 0 )
                tauxtva                 = self.GetValue( _Prix, 'Tax', 'TaxType', '01', 'TaxRatePercent', '5.5' )
                prixht                  = self.GetValue( _Prix, 'Tax', 'TaxType', '01', 'TaxableAmount', 0 )
                distributeur            = self.GetValue( _SupplyDetail, 'Supplier', 'SupplierRole', '01', 'SupplierName' )                           
                dispo_onix              = self.GetValue( _SupplyDetail, 'ProductAvailability' )  
                titre                   = self.GetValue( _TitleDetail, 'TitleElement', 'TitleElementLevel', '01', 'TitleText' )
                sous_titre              = self.GetValue( _TitleDetail, 'TitleElement', 'TitleElementLevel', '01', 'Subtitle' )
                pays                    = self.GetValue( _PublishingDetail, 'CountryOfPublication' )
                collection              = ''
                numerocollection        = '0'                
                language                = '' 
                
                #conversion de la date %Y%m%d en %m/%d/%Y
                if dateparution:
                    dateparution = time.strftime( '%m/%d/%Y', time.strptime( dateparution, '%Y%m%d' ) ) 
                
                #conversion du code dispo            
                dispo_medialivre   = 6
                if CodesDispo.has_key( dispo_onix ):
                        dispo_medialivre = CodesDispo[ dispo_onix ]
                
                
                #reconstruction du nom d'auteur
                if auteur_principal_prenom:
                    auteur_principal_prenom = ', ' + auteur_principal_prenom
                
                auteur = ''
                try:
                    auteur = Decode( auteur_principal_nom + auteur_principal_prenom )
                except:
                    print sys.exc_info()                    
                    pass
                
                #reconstruction du titre
                if sous_titre:
                    titre = titre + ' : ' + sous_titre
                    

                
                
            ################################################################################################################################          
            #assignation des données recuperées au dictionnaire.    
            self.REFS[ Product ][ 'gencod'        ] = gencod
            self.REFS[ Product ][ 'titre'         ] = Decode( titre )
            self.REFS[ Product ][ 'auteur'        ] = auteur
            self.REFS[ Product ][ 'biographie'    ] = Decode( biographie )             
            self.REFS[ Product ][ 'presentation'  ] = Decode( presentation )
            self.REFS[ Product ][ 'collection'    ] = Decode( collection )
            self.REFS[ Product ][ 'numcollection' ] = numerocollection
            self.REFS[ Product ][ 'support'       ] = support
            self.REFS[ Product ][ 'prix'          ] = prix
            self.REFS[ Product ][ 'tauxtva'       ] = tauxtva
            self.REFS[ Product ][ 'prixht'        ] = prixht
            self.REFS[ Product ][ 'dispo'         ] = dispo_medialivre
            self.REFS[ Product ][ 'distributeur'  ] = Decode( distributeur )
            self.REFS[ Product ][ 'nbpages'       ] = nbpages
            self.REFS[ Product ][ 'hauteur'       ] = hauteur            
            self.REFS[ Product ][ 'largeur'       ] = largeur
            self.REFS[ Product ][ 'epaisseur'     ] = epaisseur
            self.REFS[ Product ][ 'poids'         ] = poids
            self.REFS[ Product ][ 'image'         ] = image
            self.REFS[ Product ][ 'editeur'       ] = Decode( editeur )
            self.REFS[ Product ][ 'dateparution'  ] = dateparution
            self.REFS[ Product ][ 'pays'          ] = pays
            self.REFS[ Product ][ 'language'      ] = language
                        
            c+=1
        
        self.handle.close()
        return self.REFS                           




        
################################################################################################################################  
# *** Exemple ***         

if __name__=='__main__':
    
    REFS = {}    
        
    REFS = ParseOnix( 'XML/www.pearson.fr.xml', REFS ).WorkFile()   
    REFS = ParseOnix( 'XML/www.lesbelleslettres.com.xml', REFS ).WorkFile()    
    REFS = ParseOnix( 'XML/www.pollen-laruche.com.xml', REFS ).WorkFile()      
    REFS = ParseOnix( 'XML/extrait Hachette.xml', REFS ).WorkFile()         
    REFS = ParseOnix( 'XML/gallimard_fr_onix_20130408.xml', REFS ).WorkFile()                
    REFS = ParseOnix( 'XML/Dialogues_20130410.xml', REFS ).WorkFile()    
    REFS = ParseOnix( 'XML/Leduc20130412_0.xml', REFS ).WorkFile()
        
    for prod in REFS:    

        print '*' * 50        
        for item in REFS[ prod ]:
            
            try:
                print "%s: %s" % ( item.upper(),
                                   REFS[ prod ][item] )
            except:
                print sys.exc_info()
                pass
                
        print ""

    os.system( 'pause' )

   

