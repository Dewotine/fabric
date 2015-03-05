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

################################################
# author: cedric.bleschet@inserm.fr (2015)
# La routine install_pkg permet d'installer un paquet
# Si le nom du paquet n est pas passe en argument, il le demande
##############################################
@task
def install_pkg(pkg=None):
	""" Routine Fabric pour l installation d'un paquet. Elle prend en argument le nom du paquet.
	Si rien n'est saisie comme argument, elle redemande un nom de paquet"""
	osname = ''	# Systeme d'exploitation de la machine cible
	is_redhat=True
	if pkg is not None:
		env["pkg"] = pkg
	elif pkg is None and env.get("pkg") is None:
		env["pkg"] = prompt("Quel est le nom du paquet a installer? ")
	
	# Verifie la saisie d'un nom de paquet
	try :
		if env["pkg"] is None:
			raise ValueError("Aucun nom de paquet specifie")
	except ValueError :
		return 1
	try:
		with settings(warn_only=True):
			result = sudo("rpm -qi " + env["pkg"])
		if result.failed:
			osname = distrib_id()
			assert osname is not None
			if 'SLES' in osname:
				select_package('zypper')
				is_redhat=False
			elif osname in ['RedHatEnterpriseServer','RedHatEnterpriseES','RedHatEnterpriseAS','CentOS']:
				select_package('yum')
				is_redhat=True
			else:
				puts(red("La distribution %s n\'est pas reconnue sur le serveur %s!!!!!" % (osname,env.host)))
				return 1
			try:	
				package_install(env["pkg"])
			except e:
				puts(red(e))
				# Don't compare boolean values to True or False using == .
				# Yes:   if greeting:
				# No:    if greeting == True:
				# Worse: if greeting is True:
				if is_redhat:
					sudo("yum clean all")
				else:
					sudo("zypper clean all")
				try:
					package_install(env["pkg"])
				except:
					puts(red(e))
					return 3
			finally:
				result = sudo("rpm -qi " + env["pkg"])
				if result.failed:
					puts(red("Erreur : Le paquet %s n a pu être installe sur le serveur %s" % (env["pkg"],env.host)))
				else:
					puts(green("Le paquet %s a pu ete installe sur le serveur %s" % (env["pkg"],env.host)))
		else:
			puts(yellow("Le paquet %s est deja installe sur le serveur %s" % (env["pkg"],env.host)))
			return 2            		
	except NetworkError as network_error:
		print(red("ERROR : %s" % (network_error)))
	return 0
	

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

# La routine check_swap_usage() se base sur le fichier /proc/*/status et sur le champs VmSwap
# pour determiner la consommation de memoire swap par process. Sur RHEL4 et 5, le champs VMSwap
# n'est pas disponible. On utilise alors le champs VmSize qui donne l'utilisation de la mémoire
# virtuelle sur le serveur 
@task
def check_swap_usage():
	"""Cette routine permet de tester l\'usage de la memoire swap sur un serveur"""
	tmp_file="/tmp/swap.txt" # Fichier servant à construire le message remonté par la routine
	osname="" # Distribution sur laquelle est executee la routine
	
	# Commande pour les RHEL6, 7 et SLES 11 et 12
	cmd="for file in /proc/*/status ; do awk '/VmSwap|Name/{printf $2 \" \" $3}END{ print \"\"}' $file; done | sort -k2 -n -r | grep kB| head -15"
	# Commande Sur RHEL4 et 5, nous n'avons pas l'information de la mémoire SWAP. On indique la taille mémoire virtuelle (swap + reserved)
	cmd_rhel45="for file in /proc/*/status ; do awk '/|VmSize|Name/{printf $2 " " $3}END{ print ""}' $file; done | grep kB | sort -k 3 -n"
	with hide('output','running','warnings'), settings(warn_only=True):
		try :
			osname = distrib_id()
			if 'SLES' in osname:
				sudo("echo 'Voici les principaux processus consommant le plus de memoire SWAP sur le serveur '" + env.host + ": > " + tmp_file)
				sudo(cmd + ">> " + tmp_file)
			elif osname in ['RedHatEnterpriseServer','RedHatEnterpriseES','RedHatEnterpriseAS','CentOS']:
				sudo("echo 'Voici les principaux processus consommant le plus de memoire SWAP sur le serveur '" + env.host + ": > " + tmp_file)
				sudo(cmd + ">> " + tmp_file)
			else:
				puts(red("Distribution non reconnue"))
				exit(1)
			result = sudo ("cat " + tmp_file)
			sys.stdout.write(result+"\n")
			sudo("rm -f " + tmp_file)
			puts(green("La routine check_swap_usage s\'est terminee en succes"))
		except NetworkError as network_error:
			print(red("ERROR : %s" % (network_error)))
			
	
	
	


