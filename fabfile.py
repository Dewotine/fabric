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
from fabric.exceptions import NetworkError


################################################
#FUNCTION SET
################################################

@task
def install_pkg(pkg=None):
	""" Routine Fabric pour l installation d'un paquet. Elle prend en argument le nom du paquet. 
	Si rien n'est saisie comme argument, elle redemande un nom de paquet"""
	hst = '' # Nom d'hote de la machine cible
	osname = ''	# Systeme d'exploitation de la machine cible
	
	if pkg is not None:
		env["pkg"] = pkg
	elif pkg is None and env.get("pkg") is None:
		env["pkg"] = prompt("Quel est le nom du paquet à installer? ")
	
# Verifie la saisie d'un nom de paquet 
	try : 
		if env["pkg"] is None:
			raise ValueError("Aucun nom de paquet specifie")
	except ValueError :
		exit(4)
	
	try:
		with settings(hide('running', 'stdout')):
			# Recuperation d'information sur le serveur cible (Sors si erreur)
			hst = run('hostname')
			osname = distrib_id()
			assert osname is not None or hst is not none
			# Pour SLES
			if 'SLES' in osname:
				# warn_only=True => Le script ne s arrete pas si le paquet n est pas installe
				with settings(warn_only=True):
					# Verifie si le paquet est disponible
					if sudo("zypper search " + env["pkg"]).return_code == 0:
						puts(green("Le paquet %s a ete trouve. Installation en cours" % env["pkg"]))
					else: 
						puts(yellow("Le paquet %s n\'a pas ete trouve. Rafraichissement des données puis nouvelle tentative" % env["pkg"]))
						# Si le paquet n'a pas ete trouvé la premiere, il effectue un clean et refait la recherche
						sudo("zypper clean all")
						if sudo("zypper search " + env["pkg"]).return_code == 0:
							puts(green("Le paquet %s a ete trouve. Installation en cours" % env["pkg"]))
						else: 
							puts(red("Echec : Le paquet %s n\'a pas ete trouve!" % env["pkg"]))
							exit(3) 
					# Test si le paquet n est pas deja installe
					if sudo("rpm -qi " + env["pkg"]).return_code != 0:
						package_install_zypper(env["pkg"])
					else:
						puts(yellow("Le paquet %s est deja installe sur le serveur %s" % (env["pkg"],hst)))
						exit(2)
			# Pour Redhat
			elif osname in ['RedHatEnterpriseServer','RedHatEnterpriseES','RedHatEnterpriseAS','CentOS']:
				# warn_only=True => Le script ne s arrete pas si le paquet n est pas installe	
				with settings(warn_only=True):
					# Test si le paquet existe
					if sudo("yum info " + env["pkg"]).return_code == 0:
						puts(green("Le paquet %s a ete trouve. Installation en cours" % env["pkg"]))
					else: 
						puts(yellow(" Le paquet %s n\'a pas ete trouve. Rafraichissement des données puis nouvelle tentative" % env["pkg"]))
						# Effectue un clean et reteste si le paquet peut etre trouve
						sudo("yum clean all")
						if sudo("yum info " + env["pkg"]).return_code == 0:
							puts(green("Le paquet %s a ete trouve. Installation en cours" % env["pkg"]))
						else: 
							puts(red("Echec : Le paquet %s n\'a pas ete trouve!" % env["pkg"]))
							exit(3)
					# Installe le paquet si il n est pas deja installe
					if sudo("rpm -qi " + env["pkg"]).return_code != 0:	
						package_install_yum(env["pkg"])
					else:
						puts(yellow("Le paquet %s est deja installe sur le serveur %s" % (env["pkg"],hst)))
						exit(2)
			# Sors si la distribution n est pas listee
			else:
				puts(red("La distribution %s n\'est pas reconnue sur le serveur %s!!!!!" % (osname,hst)))
				exit(1)
			
			# Verifie si le paquet a bien ete installe. Un probleme a pu apparaitre 
			# a cause de dependance manquante, ou le serveur de depot est inaccessible 
			with settings(warn_only=True):
				if sudo("rpm -qi " + env["pkg"]).return_code == 0:
					puts(green("Le paquet %s a ete installe sur le serveur %s" % (env["pkg"],hst)))
				else: 
					puts(red("Une erreur s\'est produite pendant l\'installation du paquet %s a sur le serveur %s" % (env["pkg"],hst)))
	
	except NetworkError as network_error:
		print(red("ERROR : %s" % (network_error)))
	
	exit(0)

#@task
#def setup_postfix(pkg=None):
#	"""Configure le service postfix"""
#	postfix_conf="/etc/postfix/main.cf"
#	hst = run('hostname')
#	
#	#TODO SMTP vjf ou Mtp ???? 
#	# Utilisation des modèles !!!!

#	old_line="#relayhost = $mydomain"	
#	new_line="relayhost = smtp-prod.inserm.fr"

#	old_line2="#myhostname = host.domain.tld"
#	new_line2="myhostname = " + hst

#	old_line3="inet_protocols = all"
#	new_line3="inet_protocols = ipv4"

#	postfix_pid=process_find("postfix") 
#	if postfix_pid is None : 
#		puts(yellow("Postfix n\'est pas lance"))
#	else :
#		puts(yellow("Postfix est lance"))


#	file_update(postfix_conf, lambda mon_fichier:mon_fichier.replace(old_line,new_line))
	
@task
def check_swap_usage():
	"""Cette routine permet de tester l\'usage de la memoire swap sur un serveur"""
	tmp_file="/tmp/swap.txt" # Fichier servant à construire le message remonté par la routine
	hst="" # Nom d'hote du serveur sur lequel est executee la routine
	osname="" # Distribution sur laquelle est executee la routine
	
	# Commande pour les RHEL6, 7 et SLES 11 et 12
	cmd="for file in /proc/*/status ; do awk '/VmSwap|Name/{printf $2 \" \" $3}END{ print \"\"}' $file; done | sort -k2 -n -r | grep kB| head -15"
	# Commande Sur RHEL4 et 5, nous n'avons pas l'information de la mémoire SWAP. On indique la taille mémoire virtuelle (swap + reserved)
	cmd_rhel45="for file in /proc/*/status ; do awk '/|VmSize|Name/{printf $2 " " $3}END{ print ""}' $file; done | grep kB | sort -k 3 -n"
	with hide('output','running','warnings'), settings(warn_only=True):
		try :
			hst = run('hostname')
			osname = distrib_id()
			if 'SLES' in osname:
				sudo("echo 'Voici les principaux processus consommant le plus de memoire SWAP sur le serveur '" + hst + ": > " + tmp_file)
				sudo(cmd + ">> " + tmp_file)
				result = sudo ("cat " + tmp_file)
				sys.stdout.write(result+"\n")
			elif osname in ['RedHatEnterpriseServer','RedHatEnterpriseES','RedHatEnterpriseAS','CentOS']:
				sudo("echo 'Voici les principaux processus consommant le plus de memoire SWAP sur le serveur '" + hst + ": > " + tmp_file)
				sudo(cmd + ">> " + tmp_file)
				result = sudo ("cat " + tmp_file)
				sys.stdout.write(result+"\n")
			else:
				puts(red("Distribution non reconnue"))
				exit(1)
			sudo("rm -f " + tmp_file)
		except NetworkError as network_error:
			print(red("ERROR : %s" % (network_error)))
			exit(2)
			
	
	puts(green("La routine check_swap_usage s\'est terminee en succes"))
	exit(0)
	
	


