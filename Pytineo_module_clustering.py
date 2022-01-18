# -*- coding: utf-8 -*-
"""Pytineo_module_clustering.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/10t182zlXza0Ticbm_vk4K_7UyhWOM6Cg
"""

from IPython.core.display import display, HTML      ## élargissement de la fenêtre JUPYTER 
display(HTML("<style>.container { width:100% !important; }</style>"))

import warnings
warnings.filterwarnings('ignore')                                                                     ## ne pas faire apparaitre les messages de type Warning
import numpy as np
import pandas as pd
import math
from operator import itemgetter
from sklearn.cluster import KMeans


"""from 
le.colab import drive
drive.mount('/content/gdrive')"""

##--------------------------------
## Point d'entrée dans le module
##--------------------------------
def StartPoint(nom_commune_reference, duree_du_sejour, dict_themes, dict_sous_themes, df_POI, dict_parametres_techniques):
    
   ##  Lecture du fichier des coordonnées géographiques des communes
    df_communes = pd.read_csv("coord_geo_communes.csv")
    
   ## Attributs à transmettre au module d'affichage des cartes interactives
    for cle, valeur in dict_sous_themes.items():
        if cle == 'Restauration':
            cle_restau_bar_theme = cle
            valeur_restau_bar_theme = valeur

        if cle == 'Restauration rapide':
            cle_restau_rapide = cle
            valeur_restau_rapide = valeur        

    for cle, valeur in dict_themes.items():                
        if cle == 'Gastronomie':
            cle_gastronomie = cle
            valeur_gastronomie = valeur  

   ## moins le nombre de POI TOUR par itinéraire est élevé, plus l'itinéraire reste proche du centroïd
    max_POI_TOUR_par_itineraire = dict_parametres_techniques['max_POI_TOUR_par_itineraire']                                                                       
    alea_construction_itineraire = dict_parametres_techniques['alea_construction_itineraire']             ## l'utilisateur souhaite-t-il des itinéraires constants ou alatoires à paramétrage inchangé ?
    
    max_POI_par_itineraire = dict_parametres_techniques['max_POI_par_itineraire']                         ##nombre de POI maximum constitutifs d'un itinéraire                                                  
    min_distance_entre_2_POI = dict_parametres_techniques['min_distance_entre_2_POI']                     ## en kms     

   ## Paramètres techniques                                                                                           
    distance_max_POI_reference = dict_parametres_techniques['distance_max_POI_reference']                 ## en kms
    nbre_POI_resto_dans_perimetre_iti = dict_parametres_techniques['nbre_POI_resto_dans_perimetre_iti']   ## limitation du nombre de POI de type Restaurant (au sens générique) autour d'un itinéraire
      
    ## recherche des coordonnées géographiques de la commune sélectionnée par l'utilisateur pour effectuer son séjour
    lat_centre_commune_degre, lon_centre_commune_degre = recherche_coordonnees_geographiques(df_communes, nom_commune_reference)

    lat_centre_commune_radian = convert_degre_radian(lat_centre_commune_degre)                            ## conversion des coordonnées géographiques de degrés en radians  
    lon_centre_commune_radian = convert_degre_radian(lon_centre_commune_degre) 

    lat_reference_radian = lat_centre_commune_radian                                                      ## dans la suite du traitement, les coordonnées de référence correspondent à celles du centre de la commune
    lon_reference_radian = lon_centre_commune_radian

    ## prise en compte des thématiques de voyage de l'utilisateur pour les intégrer ou non dans les itinéraires
    df_POI = exclusion_thematiques(df_POI, dict_themes, dict_sous_themes)

    ## calcul de la distance entre le centre de la commune et chaque POI
    df_POI['Distance'] = df_POI.apply(lambda x: calcul_distance_POI_courant_autres_POI(x, lat_reference_radian, lon_reference_radian), axis=1)                                            

    ## création d'un dataframe contenant tous les POI contenus à l'intérieur du périmètre élargi de la commune
    df_POI_zoom_sur_centroid = pd.DataFrame(df_POI[df_POI['Distance'] < distance_max_POI_reference], columns=df_POI.columns)

    ## Recensement de la répartition potentielle des itinéraires par implémentation de la méthode des KMEANS
    df_POI_zoom_sur_centroid, dict_final_centroids_nbre_itineraires = affectation_itineraire_aux_centroids(df_POI_zoom_sur_centroid, duree_du_sejour, nom_commune_reference)

    ## Eclatement du dataframe source par centroïd
    dict_df_POI_zoom_sur_centroid = {}
    for cle, valeur in dict_final_centroids_nbre_itineraires.items(): 
        dict_df_POI_zoom_sur_centroid[cle] = df_POI_zoom_sur_centroid[df_POI_zoom_sur_centroid['Numéro_centroïd'] == cle]              
        
    dict_attributs_sejour = {'nom_commune_reference':nom_commune_reference, 'lat_centre_commune_degre':lat_centre_commune_degre, 'lon_centre_commune_degre':lon_centre_commune_degre, 'Restauration':'Restauration', 'Restauration souhaitee':valeur_restau_bar_theme, 'Restauration rapide':'Restauration rapide', 'Restauration rapide souhaitee':valeur_restau_rapide, 'Gastronomie':'Gastronomie', 'Gastronomie souhaitee':valeur_gastronomie, 'Nombre max POI resto-gastro souhaite':nbre_POI_resto_dans_perimetre_iti}
    
    return dict_final_centroids_nbre_itineraires, dict_df_POI_zoom_sur_centroid, dict_attributs_sejour

##-------------
## Fonctions
##-------------

def recherche_coordonnees_geographiques(df_communes, nom_commune_reference):                          ## coordonnées géographique du centre de la commune de séjour
    
    latitude = df_communes['latitude'][df_communes['nom_commune'] == nom_commune_reference].tolist()
    longitude = df_communes['longitude'][df_communes['nom_commune'] == nom_commune_reference].tolist()
    return latitude[0], longitude[0]

def convert_degre_radian(angle_en_degres):                                                             ## conversion des degrés en radians
    return (np.pi * angle_en_degres)/180

def calcul_distance_POI_courant_autres_POI(x, lat_ref_radian, lon_ref_radian):                        ## calcul distance entre le point de référence et les POI
                              
    lat_POI_radian = convert_degre_radian(x['Latitude'])                
    lon_POI_radian = convert_degre_radian(x['Longitude'])  
    
    distance = formule_calcul_distance(lat_ref_radian, lon_ref_radian, lat_POI_radian, lon_POI_radian)                 
    return distance

def formule_calcul_distance(lat_ref_radian, lon_ref_radian, lat_POI_radian, lon_POI_radian):
    
    R = 6371  
    distance = R * 2 * math.asin(math.sqrt(math.sin((lat_ref_radian - lat_POI_radian)/2) * math.sin((lat_ref_radian - lat_POI_radian)/2)
                     + math.cos(lat_ref_radian) * math.cos(lat_POI_radian) * math.sin((lon_ref_radian - lon_POI_radian)/2) * math.sin((lon_ref_radian - lon_POI_radian)/2)))
    return distance

def exclusion_thematiques(df_POI, dict_themes, dict_sous_themes):

    liste_exclusion_theme = []
    for cle, valeur in dict_themes.items():
        if not valeur:
            liste_exclusion_theme.append(cle)
    
    if len(liste_exclusion_theme) != 0:
        df_POI = df_POI[~df_POI['Thématique_POI'].isin(liste_exclusion_theme)]  
            
    liste_exclusion_sous_theme = []
    for cle, valeur in dict_sous_themes.items():
        if not valeur:
            liste_exclusion_sous_theme.append(cle)
    
    if len(liste_exclusion_sous_theme) != 0:
        df_POI = df_POI[~df_POI['Mot_clé_POI'].isin(liste_exclusion_sous_theme)]        

    return df_POI

def affectation_itineraire_aux_centroids(df_POI_zoom_sur_centroid, duree_du_sejour, nom_commune_reference):
    
    df_POI_KMEANS = pd.DataFrame({'Latitude': df_POI_zoom_sur_centroid['Latitude'], 'Longitude': df_POI_zoom_sur_centroid['Longitude']})

    print('----------------------------------------------------------------------------------------------------------')
    print('Application de la méthode de clustering KMEANS à la commune', '(', nom_commune_reference, ')', 'et à la durée du séjour', '(', duree_du_sejour, ') :')
    print('----------------------------------------------------------------------------------------------------------', '\n')   

   ## Utilisation de la fonction de répartition euclidienne pour évaluer la répartition projetée des itinéraires, en fonction du nombre de jours du séjour
    clf = KMeans(n_clusters = duree_du_sejour, random_state=66)
    clf.fit(df_POI_KMEANS) 
    labels = clf.labels_
    centroids = clf.cluster_centers_

    print('Centroïds résultants :', list(centroids), '\n') 
    print('Labels résultants :', list(labels), '\n') 

    dict_centroids_nbre_itineraires = {}
    for index, valeur in enumerate(centroids):                                                            ## alimentation dictionnaire numéro/coordonnées centroïds 
        liste_attributs_centroids = []
        liste_attributs_centroids.append(valeur[0])
        liste_attributs_centroids.append(valeur[1])
        dict_centroids_nbre_itineraires[index] = liste_attributs_centroids

    nombre_total_labels = 0                                                                               ## nombre total de labels (donc de POI)
    for i in labels:
        nombre_total_labels +=1   

    for i in range(0, duree_du_sejour):                                                                   ## initialisation des compteurs de labels par centroïd 
        globals()[f"cpt_label_{i}"] = 0  

    for i in labels:                                                                                      ## comptage du nombre de labels par centroïds
        globals()[f"cpt_label_{i}"] += 1

    dict_centroids_labels = {}       
    for i in range(0, duree_du_sejour):                                                                   ## association n° de centroïd/Nombre de labels sous forme de dictionnaire 
        dict_centroids_labels[i] = globals()[f"cpt_label_{i}"]

    dict_centroids_labels_trie = {}
    for cle, valeur in sorted(dict_centroids_labels.items(), key=itemgetter(1), reverse=True):            ## tri du dictionaire par ordre décroissant de valeurs
        dict_centroids_labels_trie[cle] = valeur

    print('--------------------------------------------------------------')
    print('Construction de la répartition des itinéraires par centroïd :')
    print('--------------------------------------------------------------', '\n')    

    print('Dictionnaire des centroids/nombre de labels trié en décroissance de nombre de labels :', dict_centroids_labels_trie, '\n') 

    liste_no_centroid_nbre_iti = []
    liste_no_centroid_part_decimale = []
    nbre_occurrences_centroïds_traites = 0 

    for cle, valeur in dict_centroids_labels_trie.items():                                                ## affectation de 0 à n itinéraires à chaque centroïd, au prorata de son nombre de POI                                              
        ratio = valeur / nombre_total_labels
        nbre_iti_par_centroid = round(ratio*duree_du_sejour)
        partie_decimale = abs((ratio*duree_du_sejour) - nbre_iti_par_centroid)
        liste_temporaire = []
        liste_temporaire.append(cle)
        liste_temporaire.append(partie_decimale)
        liste_no_centroid_part_decimale.append(liste_temporaire)

        liste_temporaire = []
        liste_temporaire.append(cle)
        liste_temporaire.append(nbre_iti_par_centroid)
        liste_no_centroid_nbre_iti.append(liste_temporaire)
        nbre_occurrences_centroïds_traites += nbre_iti_par_centroid      

    print('Liste nombre itinéraire par centroïd AVANT prise en compte de la partie décimale :', liste_no_centroid_nbre_iti, '\n') 

    if nbre_occurrences_centroïds_traites < duree_du_sejour:                                              ## s'il reste des itinéraires non affectés, ils sont alloués aux centroïds dont la partie décimale
        for centroid_decimal in liste_no_centroid_part_decimale:                                          ## dont les parties décimales calculées précédemment sont les plus importantes
            for i, centroid_nbre_iti in enumerate(liste_no_centroid_nbre_iti):
                if centroid_decimal[0] ==  centroid_nbre_iti[0]:                
                    liste_no_centroid_nbre_iti[i][1] +=1
                    nbre_occurrences_centroïds_traites +=1  
            if nbre_occurrences_centroïds_traites == duree_du_sejour:
                break

    liste_no_centroid_part_decimale = sorted(liste_no_centroid_part_decimale, key=itemgetter(1), reverse=True)
    print('Liste des parties décimales, par centroïd :', liste_no_centroid_part_decimale, '\n')   

    print('Liste nombre itinéraire par centroïd APRES prise en compte de la partie décimale :', liste_no_centroid_nbre_iti, '\n') 

    dict_centroids_itineraires = {}
    nbre_centroids_temp = duree_du_sejour

    for centroid_nbre_iti in liste_no_centroid_nbre_iti:                                                  ## regroupement des itinéraires par centroïd    
        no_centroid = centroid_nbre_iti[0]                                                                ## en sortie, les centroïds contenant de nombreux POI regrouperont plusieurs itinéraires, tandis que 
        nbre_iti = centroid_nbre_iti[1]                                                                   ## ceux en contenant proportionnellement trop peu ne seront pas retenus 

        liste_itineraires_par_centroid = []

        if nbre_iti >= 1:    
            liste_itineraires_par_centroid.append(no_centroid)
            if nbre_iti > 1:
                for i in range(0, nbre_iti+1):                                                            ## les numéros de centroïd sans itinéraire correspondant sont regroupés avec numéros de centroïd concernés
                    if liste_no_centroid_nbre_iti[nbre_centroids_temp-1][1] == 0:
                        liste_itineraires_par_centroid.append(liste_no_centroid_nbre_iti[nbre_centroids_temp-1][0])
                        nbre_centroids_temp -=1

        if nbre_iti != 0:     
            dict_centroids_itineraires[no_centroid] = liste_itineraires_par_centroid                    

    print('Dictionnaire de réaffectation des numéros de centroïds sans itinéraire(s) aux centroïd éligibles :', dict_centroids_itineraires, '\n')  

    ## rénumérotation des labels en fonction des regroupements de centroïds contenu dans le dictionnaire final
    liste_finale_labels = []
    for no_cluster_lab in labels:
        for cle, liste_clusters in dict_centroids_itineraires.items():
            for no_cluster_dict in liste_clusters:
                if no_cluster_lab == no_cluster_dict:
                    liste_finale_labels.append(cle)

    print('Affectation FINALE des labels aux centroïds :', liste_finale_labels, '\n') 

    ## enrichissement du dictionnaire inital contenant les numéros et coordonnées centroïds du nombre d'itinéraires concernant chacun d'entre eux
    dict_final_centroids_nbre_itineraires = {}
    nbre_centroids_finaux = 0
    for cle_1, valeur_1 in dict_centroids_nbre_itineraires.items():
        cpt_itineraires = 0
        centroid_avec_itineraire = False
        liste_temporaire = dict_centroids_nbre_itineraires[cle_1]
        for cle_2, valeur_2 in dict_centroids_itineraires.items():
            if cle_1 == cle_2:
                centroid_avec_itineraire = True
                for i in range(0, len(valeur_2)):
                    cpt_itineraires +=1

        if centroid_avec_itineraire:
            nbre_centroids_finaux +=1
            liste_temporaire.append(cpt_itineraires)        
            dict_final_centroids_nbre_itineraires[cle_1] = liste_temporaire
        
    print('Centroïd (numéro/coordonnées géographiques/nombre d\'itinéraires) :', dict_final_centroids_nbre_itineraires, '\n')   

    ## ajout d'une colonne au dataframe de label d'appartenance du POI à son centroid
    df_POI_zoom_sur_centroid = df_POI_zoom_sur_centroid.assign(Numéro_centroïd = liste_finale_labels)        

    return df_POI_zoom_sur_centroid, dict_final_centroids_nbre_itineraires







