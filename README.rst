Tadpoles.com Scraper
==============================

WHAT
++++

Tadpoles.com is a site where daycare centers sometimes post 
pics of kids if they use the tadpoles ipad app. They don't support
bulk downloads though...until now. 

Dependencies
+++++++++++++

* Heroku
* Google Cloud Storage

Usage
+++++

1) Create a service account in GCS and give it Storage Admin Role
2) Export the credential as a .json file
3) create a dyno on heroku and add the mongodb and heroku scheduler addons
4) set the following config vars with values from the key.json file downloaded from GCS (in project config in Heroku)
* gcs_private_key
* gcs_client_email
* gcs_private_key_id
* gcs_client_id
* gcs_project_id
* gcs_client_x509_cert_url
5) Launch console in heroku, and run:
    $ python py/app.py
6) Once cookie is established, setup Heroku scheduler to run 'python py/app.py' on periodic basis
