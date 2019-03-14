#!/usr/bin/python
# _*_ coding: utf-8 _*_
##########################################################################################################################
# auteur  : FrGr
# datcre  : 04/12/2012
# datmaj  : 14/03/2019
# version : 1.5
# notes   : adaptation aux formats ONIX 2.1 et 3.0
#           détection automatique du format et de la référence 12/04/2013
#           harmonisation du flux obtenu en sortie
#
#           la liste des champs récupérés dans cette librairie n'est pas exhaustive
#           et doit être finalisée pour une lecture complète des flux onix
##########################################################################################################################


import time, sys, os, re
import xml.etree.ElementTree as etree
from HTMLParser import HTMLParser


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
                              'dispo'        : '0',
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
        
        #compteur de produits dans le flux
        self.count   = 0

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


    def GetValue( self,
                  node,
                  o_tag_to_match,
                  o_id_to_match='',
                  value_to_match='',
                  o_field_name='',
                  default='' ):

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

                list_to_match = value_to_match.split( '~' )

                for item in d:
                    if ( d[item].has_key( field_name ) and
                         d[item].has_key( id_to_match ) ):
                         
                        if d[item][ id_to_match ] in list_to_match:
                            try:
                                if eval( d[item][ field_name ] ) == 0:
                                    d[item][ field_name ] = default
                            except:
                                pass
                                
                            return d[item][ field_name ]

        return default


    def WorkFile( self ):
        
        ProdList = self.Root.findall( '%sProduct' % self.ref )
        
        for Product in ProdList:

            #modification yield au lieu de return -> on renvoie une hashtable "propre"
            #a chaque iteration
            self.REFS = {}

            #on initialise le dico Product à l'interieur du dico REFS
            self.REFS = self.DefaultDico
            
            try:
                #récupération de la donnée gencod commune aux flux 2.1 et 3
                gencod = self.GetValue( Product, 'ProductIdentifier', 'ProductIDType', '15~03', 'IDValue' )

                ###################
                #Format ONIX 2.1
                if self.Release == '2.1':

                    #elements XML
                    _SupplyDetail           = self.GetValue( Product, 'SupplyDetail' )
                    _Series                 = self.GetValue( Product, 'Series' )

                    #elements textes spécifiques à la version 2.1
                    titre                   = self.GetValue( Product, 'Title', 'TitleType', '01', 'TitleText' )
                    auteur_principal_prenom = self.GetValue( Product, 'Contributor', 'ContributorRole', 'A01~B05', 'NamesBeforeKey' )
                    auteur_principal_nom    = self.GetValue( Product, 'Contributor', 'ContributorRole', 'A01~B05', 'KeyNames' )
                    biographie              = self.GetValue( Product, 'Contributor', 'ContributorRole', 'A01~B05', 'BiographicalNote' )
                    presentation            = self.GetValue( Product, 'OtherText', 'TextTypeCode', '01', 'Text' )
                    collection              = self.GetValue( _Series, 'TitleOfSeries' )
                    numerocollection        = self.GetValue( _Series, 'NumberWithinSeries', '', '' ,'', 0 )
                    support                 = self.GetValue( Product, "ProductForm" )
                    prix                    = self.GetValue( _SupplyDetail, 'Price', 'PriceTypeCode', '04~02', 'PriceAmount', 0 )
                    tauxtva                 = self.GetValue( _SupplyDetail, 'Price', 'PriceTypeCode', '04~02', 'TaxRatePercent1', '5.5' )
                    prixht                  = self.GetValue( _SupplyDetail, 'Price', 'PriceTypeCode', '04~02', 'TaxableAmount1', 0 )
                    dispo_onix              = self.GetValue( _SupplyDetail, 'ProductAvailability' )
                    distributeur            = self.GetValue( _SupplyDetail, 'SupplierName' )
                    nbpages                 = self.GetValue( Product, 'NumberOfPages', '', '', '', 0 )
                    hauteur                 = self.GetValue( Product, 'Measure', 'MeasureTypeCode', '01', 'Measurement', 0 )
                    largeur                 = self.GetValue( Product, 'Measure', 'MeasureTypeCode', '02', 'Measurement', 0 )
                    epaisseur               = self.GetValue( Product, 'Measure', 'MeasureTypeCode', '03', 'Measurement', 0 )
                    poids                   = self.GetValue( Product, 'Measure', 'MeasureTypeCode', '08', 'Measurement', 0 )
                    image                   = self.GetValue( Product, 'MediaFile', 'MediaFileTypeCode', '02~04~06', 'MediaFileLink' )
                    editeur                 = self.GetValue( Product, 'Publisher', 'PublishingRole', '01', 'PublisherName' )
                    dateparution            = self.GetValue( Product, 'PublicationDate' )
                    pays                    = self.GetValue( Product, 'CountryOfPublication' )
                    language                = self.GetValue( Product, 'Language', 'LanguageRole', '01~02', 'LanguageCode' )


                    ########################
                    #infos alternatives ####
                    if not editeur:
                        editeur                 = self.GetValue( Product, 'Imprint', 'NameCodeType', '06~02~01', 'ImprintName' )

                    if not auteur_principal_nom:
                        auteur_principal_nom    = self.GetValue( Product, 'Contributor', 'ContributorRole', 'A01~B05', 'PersonNameInverted' )



                ###################
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
                    support                 = self.GetValue( _DescriptiveDetail, 'ProductForm' )
                    auteur_principal_prenom = self.GetValue( _DescriptiveDetail, 'Contributor', 'ContributorRole', 'A01~B05', 'NamesBeforeKey' )
                    auteur_principal_nom    = self.GetValue( _DescriptiveDetail, 'Contributor', 'ContributorRole', 'A01~B05', 'KeyNames' )
                    biographie              = self.GetValue( _DescriptiveDetail, 'Contributor', 'ContributorRole', 'A01~B05', 'BiographicalNote' )
                    hauteur                 = self.GetValue( _DescriptiveDetail, 'Measure', 'MeasureType', '01', 'Measurement', 0 )
                    largeur                 = self.GetValue( _DescriptiveDetail, 'Measure', 'MeasureType', '02', 'Measurement', 0 )
                    epaisseur               = self.GetValue( _DescriptiveDetail, 'Measure', 'MeasureType', '03', 'Measurement', 0 )
                    poids                   = self.GetValue( _DescriptiveDetail, 'Measure', 'MeasureType', '08', 'Measurement', 0 )
                    presentation            = self.GetValue( _CollateralDetail, 'TextContent', 'TextType', '03', 'Text' )
                    image                   = self.GetValue( _SupportingResource, 'ResourceVersion',  'ResourceForm', '02~04~06', 'ResourceLink' )
                    nbpages                 = self.GetValue( _TextItem, 'NumberOfPages', '', '', '', 0 )
                    editeur                 = self.GetValue( _PublishingDetail, 'Publisher', 'PublishingRole', '01', 'PublisherName' )
                    dateparution            = self.GetValue( _PublishingDetail, 'PublishingDate', 'PublishingDateRole', '01', 'Date' )
                    prix                    = self.GetValue( _SupplyDetail, 'Price', 'PriceType', '04~02~01', 'PriceAmount', 0 )
                    tauxtva                 = self.GetValue( _Prix, 'Tax', 'TaxType', '01', 'TaxRatePercent', '5.5' )
                    prixht                  = self.GetValue( _Prix, 'Tax', 'TaxType', '01', 'TaxableAmount', 0 )
                    distributeur            = self.GetValue( _SupplyDetail, 'Supplier', 'SupplierRole', '01', 'SupplierName' )
                    dispo_onix              = self.GetValue( _SupplyDetail, 'ProductAvailability' )
                    titre                   = self.GetValue( _TitleDetail, 'TitleElement', 'TitleElementLevel', '01', 'TitleText' )
                    sous_titre              = self.GetValue( _TitleDetail, 'TitleElement', 'TitleElementLevel', '01', 'Subtitle' )
                    pays                    = self.GetValue( _PublishingDetail, 'CountryOfPublication' )

                    #données non récupérées en v3
                    collection              = ''
                    numerocollection        = '0'
                    language                = ''

                    #reconstruction du titre
                    if sous_titre:
                        titre = titre + ' : ' + sous_titre


                ######################################################
                # post traitements communs v2.1 et v3 ################

                #conversion de la date %Y%m%d en %m/%d/%Y
                if dateparution:
                    dateparution = time.strftime( '%m/%d/%Y', time.strptime( dateparution, '%Y%m%d' ) )

                #reconstruction du nom d'auteur
                if auteur_principal_prenom:
                    auteur_principal_prenom = ', ' + auteur_principal_prenom

                auteur = ''
                try:
                    auteur = Decode( auteur_principal_nom + auteur_principal_prenom )
                        
                except:
                    print sys.exc_info()
                    pass

                ####################################################
                #assignation des données recuperées au dictionnaire.
                self.REFS[ 'gencod'        ] = gencod
                self.REFS[ 'titre'         ] = Decode( titre )
                self.REFS[ 'auteur'        ] = auteur
                self.REFS[ 'biographie'    ] = Decode( biographie )
                self.REFS[ 'presentation'  ] = Decode( presentation )
                self.REFS[ 'collection'    ] = Decode( collection )
                self.REFS[ 'numcollection' ] = numerocollection
                self.REFS[ 'support'       ] = support
                self.REFS[ 'prix'          ] = prix
                self.REFS[ 'tauxtva'       ] = tauxtva
                self.REFS[ 'prixht'        ] = prixht
                self.REFS[ 'dispo'         ] = dispo_onix
                self.REFS[ 'distributeur'  ] = Decode( distributeur )
                self.REFS[ 'nbpages'       ] = nbpages
                self.REFS[ 'hauteur'       ] = hauteur
                self.REFS[ 'largeur'       ] = largeur
                self.REFS[ 'epaisseur'     ] = epaisseur
                self.REFS[ 'poids'         ] = poids
                self.REFS[ 'image'         ] = image
                self.REFS[ 'editeur'       ] = Decode( editeur )
                self.REFS[ 'dateparution'  ] = dateparution
                self.REFS[ 'pays'          ] = pays
                self.REFS[ 'language'      ] = language

                self.count+=1

                yield self.REFS
            
            except:
                print sys.exc_info()
                pass

################################################################################################################################
# *** Exemple ***

if __name__=='__main__':

    try:
        P = ParseOnix( 'www.pearson.fr.xml' )
        for prod in P.WorkFile():

            #prod correspond a une iteration sous forme de hashtable
            for cle in prod:
                print "%s: %s" % ( cle.upper(), prod[cle] )

            print '*' * 50

    except:
        print sys.exc_info()
        pass
        
    os.system( 'pause' )



