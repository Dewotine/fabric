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
#from fabric.exceptions import NetworkError
from fabric.exceptions import *

################################################
#FUNCTION SET
################################################

################################################
# author: cedric.bleschet@inserm.fr (2015)
# La routine install_pkg permet d'installer un paquet
# Si le nom du paquet n est pas passe en argument, il le demande
##############################################
@task
def install_pkg(*pkg):
	""" Routine pour l installation d'un ou plusieurs paquets. Elle prend en argument le nom du paquet. Si rien n'est saisie comme argument, elle redemande un nom de paquet"""
	osname = '' # Systeme d'exploitation de la machine cible
	result='' # resultat de la premiere tentative d'installation
	result2='' # resultat de la seconde tentative d'installation
	#env.abort_on_prompts = True

	# Verification du nom de paquet
	with hide('running','output','warnings'):
		try:
			if pkg:
				env["pkg"] = pkg
			else:
				raise ValueError("Aucun nom de paquet specifie")
				puts(yellow("Aucun nom de paquet specifie en argument"))
		except ValueError:
			try:
				env["pkg"] = prompt("Quel est le nom du paquet a installer? ")
				if not env["pkg"]:
					raise ValueError
			except ValueError:
				puts(red("Aucun nom de paquet"))
				return 1

	        # Envoie des commandes d'installation sur le serveur cible
		try:
            		for packet in env["pkg"]:
                		with settings(warn_only=True):
                		#Verifie si le paquet est deja instale
	                    		result = sudo("rpm -qi " + packet)
                			if result.failed:
                    				osname = distrib_id()
                    				assert osname is not None
                    				if 'SLES' in osname:
                        				select_package('zypper')
                    				elif osname in ['RedHatEnterpriseServer','RedHatEnterpriseES','RedHatEnterpriseAS','CentOS']:
                        				select_package('yum')
                    				else:
                        				puts(red("La distribution %s n\'est pas reconnue sur le serveur %s!!!!!" % (osname,env.host)))
                        				return 1
                				# Installation du paquet
                    				try:
                        				with settings(warn_only=True):
                            					package_install(packet)
                        				sudo("rpm -qi " + packet)
                    				except:
                        				# nettoie le cache et retente l installation
                        				puts("2e tentative avec nettoyage du cache")
                        				package_clean()
                        				with settings(warn_only=True):
                            					package_install(packet)
                				# Verifie si le paquet a bien pu s installer
                    				finally:
                        				with settings(warn_only=True):
                            					result = sudo("rpm -qi " + packet)
                        				if result.failed:
                            					puts(red("Erreur : Le paquet %s n\'a pu etre installe sur le serveur %s" % (packet,env.host)))
                        					return 3
                        				else:
                            					puts(green("Le paquet %s a pu ete installe sur le serveur %s" % (packet,env.host)))
                			else:
                    				puts(yellow("Le paquet %s est deja installe sur le serveur %s" % (packet,env.host)))
        
	# En cas de probleme de connexion au serveur cible
	except NetworkError as network_error:
		print(red("ERROR : %s" % (network_error)))
		return 4

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
	"""Cette routine permet d'obtenir le detail sur l\'usage de la memoire swap sur un serveur"""
	tmp_file="/tmp/swap.txt" # Fichier servant a construire le message remonter la routine
    	osname="" # Distribution sur laquelle est executee la routine
    	rhel_version = ""
    	sles_version = ""

    	# Commande pour les RHEL6, 7 et SLES 11 et 12
    	cmd="for file in /proc/*/status ; do awk '/VmSwap|Name/{printf $2 \" \" $3}END{ print \"\"}' $file 2 > /dev/null; done | sort -k2 -n -r | grep kB| head -15"
     	#Commande Sur RHEL4 et 5, nous n'avons pas l'information de la memoire SWAP. On indique la taille memoire virtuelle (swap + reserved)
    	cmd_rhel45="for file in /proc/*/status ; do awk '/Uid|Tgid|VmSize|Name/{printf $2 \" \" $3}END{ print \"\"}' $file 2> /dev/null; done | grep kB | cut -d \" \" -f1,3,4 | sort -k2 -n -r |  head -15"

    	with hide('status','aborts','stdout','warnings','running','stderr'):
        	try :
            		osname = distrib_id()
            		if 'SLES' in osname:
                		sles_version = find_os_distro_cbl()
                		if sles_version == "sles11SP1":
                    			print("Impossible de savoir quel processus consomme le plus de RAM sur SLES 11 SP1")
                    			print("Les processus consommant le plus de memoire (vive + SWAP) sur le serveur %s sont" %env.host)
                    			result = sudo(cmd_rhel45)
                		else:
                    			print("Les processus consommant le plus de memoire SWAP sur le serveur %s sont" %env.host)
                    			result = sudo(cmd)
            		elif osname in ['RedHatEnterpriseServer','RedHatEnterpriseES','RedHatEnterpriseAS','CentOS']:
                		rhel_version=find_os_distro_cbl()
                		if rhel_version == "redhat4" or rhel_version == "redhat5":
                    			print("Impossible de savoir quel processus consomme le plus de RAM sur RHEL 4 ou 5")
                    			print("Les processus consommant le plus de memoire (vive + SWAP) sur le serveur %s sont" %env.host)
                    			result = sudo(cmd_rhel45)
                		elif rhel_version == "redhat6" or rhel_version == "redhat7":
                    			print("Les processus consommant le plus de memoire SWAP sur le serveur %s sont" %env.host)
                    			result = sudo(cmd)
                		else:
                    			puts(red("Impossible de reconnaitre de version de redhat utilisee"))
                    			exit(1)
            		else:
                		puts(red("Distribution non reconnue"))
                		exit(1)
            		print(result)
            		puts(green("La routine check_swap_usage s\'est terminee en succes"))
        	except NetworkError as network_error:
            		print(red("ERROR : %s" % (network_error)))

			
#############################################
# author: cedric.bleschet@inserm.fr (2015)
# La routine install_pkg permet d'installer un paquet
# Si le nom du paquet n est pas passe en argument, il le demande
##############################################
@task
def update_pkg(*pkg):
	""" Routine Fabric pour la mise a jour d'un paquet. Elle prend en argument le nom du paquet.
	Si rien n'est saisie comme argument, elle redemande un nom de paquet"""
	osname = '' # Systeme d'exploitation de la machine cible
	#env.abort_on_prompts = True
	update_result = ''
	
	# Verification du nom de paquet
	with hide('running','output','warnings'):
		try:
			if pkg:
				env["pkg"] = pkg
			else:
				raise ValueError("Aucun nom de paquet specifie")
				puts(yellow("Aucun nom de paquet specifie en argument"))
		except ValueError:
			try:
				env["pkg"] = prompt("Quel est le nom du paquet a installer? ")
				if not env["pkg"]:
					raise ValueError
			except ValueError:
				puts(red("Aucun nom de paquet"))
				return 1

	try:
		osname = distrib_id()
		assert osname is not None
		with hide('running','output','warnings'):
			# Pour SLES
			if 'SLES' in osname:
				try:
					sudo ("zypper --non-interactive refresh")
					for packet in env["pkg"]:
						update_result = sudo("zypper --non-interactive update " + packet)
						if update_result.find("Error") == 0 :
							puts(red("Une erreur s\'est produite pendant la mise du paquet %s a sur le serveur %s" % (packet,env.host)))
							return 2
						else:
							puts(green("Le paquet %s a ete mis a jour sur le serveur SLES %s" % (packet,env.host)))
				except SystemExit:
		                	puts(red("Une erreur s\'est produite en tentant de metre a jour le serveur SLES %s" % env.host))
			# Pour Redhat
			elif osname in ['RedHatEnterpriseServer','RedHatEnterpriseES','RedHatEnterpriseAS','CentOS']:
				try:
					sudo ("yum clean all")
					for packet in env["pkg"]:
						try:
							sudo("yum -y update " + packet)
						except SystemExit:
							puts(red("Une erreur s\'est produite pendant la mise a jour du paquet %s sur le serveur RHEL %s")% (packet,env.host))
						else:
							puts(green("Le paquet %s a ete mis a jour sur le serveur %s" % (packet,env.host)))
			else:
				puts(red("Impossible de reconnaitre le type de serveur"))
				return 1

	except NetworkError as network_error:
		print(red("ERROR : %s" % (network_error)))	


