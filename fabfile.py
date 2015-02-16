#!/usr/bin/python
# -*-coding:utf-8 -*
################################################
#    FABRIC FILE PRODUCTION ENVIRONMENT
##################################################


################################################
#LIBRARIES LOADING
################################################
from fabric.api import *
from cuisine import *
from fabric.utils import puts
from fabric.colors import *
from fabtools.system import * # pour distrib_id


################################################
#FUNCTION SET
################################################

@task
def install_pkg(pkg=None):
	hst = run('hostname')
	osname = distrib_id()

	# Verification du contenu de la varaiable osname. Pour les distribution SLES,
	# distrib_id ne renvoie rien 
	assert osname is not None or hst is not none
	
	
	if pkg is not None:
		env["pkg"] = pkg
	elif pkg is None and env.get("pkg") is None:
		env["pkg"] = prompt("Quel est le nom du paquet à installer? ")
	# Verifie si le paquet est disponible 
	try : 
		if env["pkg"] is None:
			raise ValueError("Aucun nom de paquet specifie")
	except ValueError :
		return 4
	
	# Verifie si le paquet n'est pas deja installe
	with settings(hide('running', 'stdout')):
		if 'SLES' in osname:
			# warn_only=True => Le script ne s arrete pas si le paquet n est pas installe
			with settings(warn_only=True):
				# Verifie si le paquet est disponible
				if sudo("zypper search " + env["pkg"]).return_code == 0:
					puts(green("Le paquet %s a ete trouve. Installation en cours" % env["pkg"]))
				else: 
					puts(yellow("Le paquet %s n\'a pas ete trouve. Rafraichissement des données puis nouvelle tentative" % env["pkg"]))
					sudo("zypper clean all")
					if sudo("zypper search " + env["pkg"]).return_code == 0:
						puts(green("Le paquet %s a ete trouve. Installation en cours" % env["pkg"]))
					else: 
						puts(red("Echec : Le paquet %s n\'a pas ete trouve!" % env["pkg"]))
						return 3 
				if sudo("rpm -qi " + env["pkg"]).return_code != 0:
					package_install_zypper(env["pkg"])
				else:
					puts(yellow("Le paquet %s est deja installe sur le serveur %s" % (env["pkg"],hst)))
					return 2
		elif osname in ['RedHatEnterpriseServer','RedHatEnterpriseES','RedHatEnterpriseAS','CentOS']:
			# warn_only=True => Le script ne s arrete pas si le paquet n est pas installe	
			with settings(warn_only=True):
				if sudo("yum info " + env["pkg"]).return_code == 0:
					puts(green("Le paquet %s a ete trouve. Installation en cours" % env["pkg"]))
				else: 
					puts(yellow(" Le paquet %s n\'a pas ete trouve. Rafraichissement des données puis nouvelle tentative" % env["pkg"]))
					sudo("yum clean all")
					if sudo("yum info " + env["pkg"]).return_code == 0:
						puts(green("Le paquet %s a ete trouve. Installation en cours" % env["pkg"]))
					else: 
						puts(red("Echec : Le paquet %s n\'a pas ete trouve!" % env["pkg"]))
						return 3
				if sudo("rpm -qi " + env["pkg"]).return_code != 0:	
					package_install_yum(env["pkg"])
				else:
					puts(yellow("Le paquet %s est deja installe sur le serveur %s" % (env["pkg"],hst)))
					return 2
		else:
			puts(red("La distribution %s n\'est pas reconnue sur le serveur %s!!!!!" % (osname,hst)))
			return 1

		with settings(warn_only=True):
			if sudo("rpm -qi " + env["pkg"]).return_code == 0:
				puts(green("Le paquet %s a ete installe sur le serveur %s" % (env["pkg"],hst)))
			else: 
				puts(red("Une erreur s\'est produite pendant l\'installation du paquet %s a sur le serveur %s" % (env["pkg"],hst)))
	return 0

