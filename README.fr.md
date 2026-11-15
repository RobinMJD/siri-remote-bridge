# Siri Remote Bridge

Ce projet permet de recevoir une Siri Remote en Bluetooth sur une machine Linux,
puis de transmettre ses boutons a Home Assistant pour piloter Apple TV par le
reseau. Il est utile lorsque l'Apple TV est dans un meuble ou hors de portee.

L'installation ne necessite pas une nouvelle VM : un Linux existant, une VM avec
adaptateur USB dedie ou une carte Linux compatible BlueZ peut convenir. Le
protocole d'entree reste celui de Siri Remote ; les autres marques de
telecommandes ne sont pas automatiquement compatibles.

Le [guide complet en anglais](README.md) couvre installation, appairage volontaire,
securite, configuration Home Assistant, sauvegarde/restauration et maintenance.
Les donnees privees et secrets restent hors du depot.

- Redemarrage automatique des conteneurs, sauf arret volontaire.
- Reconnexion au lien Bluetooth deja appaire, sans adopter une autre remote.
- Appui court au centre : selection au relachement ; maintien : menu contextuel.
- Appui court Power : menu d'alimentation si allume, reveil sinon ; maintien : veille.
- Maintien Home : Centre de controle ; maintien Retour : ecran d'accueil.
- Pas de Siri/microphone, gestes tactiles ou double-clic dans cette version.

Version initiale : les tests logiciels et essais physiques ne garantissent pas
la compatibilite de tous les adaptateurs, versions ou montages HDMI-CEC.
Voir la [matrice de validation](docs/validation.md) pour les limites exactes.
