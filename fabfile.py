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
from fabric.contrib import * # (pour la méthode append)
import os
import re

################################################
#FUNCTION SET
################################################

################################################
# author: cedric.bleschet@inserm.fr (2015)
# Modification de find_os_distro
# Renvoie la version de rhel
################################################
def find_os_distro_cbl():
	if file_exists('/etc/redhat-release'):
		ret = file_read('/etc/redhat-release')
		if 'Red' or 'CentOS' in ret:
			if command_check('/usr/bin/yum'):
				if 'release 4' in ret:
					puts ('RHEL4')
					return "redhat4"
				elif 'release 5.10' in ret:
					puts ('RHEL5')
					return "redhat5"
				elif ('release 6.3' or 'release 6.5') in ret:
					puts ('RHEL6')
					return "redhat6"
				elif 'release 7' in ret:
					puts ('RHEL7')
					return "redhat7"
				else:
					puts(red("Version de RHEL non reconnu"))
	if file_exists('/etc/SuSE-release'):
		ret = file_read('/etc/SuSE-release')
		if 'SUSE' and '11' in ret:
			if command_check('/usr/bin/zypper'):
				sles_version = int(sudo('grep PATCHLEVEL /etc/SuSE-release | cut -d"=" -f2'))
				if sles_version == 1:
					return "sles11SP1"
				elif sles_version == 2:
					return "sles11SP2"
				elif sles_version == 3:
					return "sles11SP3"
				else:
					puts(red("Version de SLES non reconnu"))
		elif 'SUSE' and '12' in ret:
			if command_check('/usr/bin/zypper'):
				return "sles12"


################################################
# author: cedric.bleschet@inserm.fr (2015)
# La routine install_pkg permet d'installer un ou plusieurs paquets.
# Si le nom du paquet n est pas passe en argument, il le demande.
##############################################
@task
def install_pkg(*pkg):
    """ Install one or several packet passed as parameter. If no package name is indicated, the script will ask for one"""
    osname = ''	# Systeme d'exploitation de la machine cible

    # Verification du nom de paquet
    with hide('status','aborts','stdout','warnings','running','stderr'):
        try:
            if pkg:
                env["pkg"] = pkg
            else:
                raise ValueError("")
                puts(yellow("No package name specified"))
        except ValueError:
            try:
                env["pkg"] = prompt("Which package should be installed")
                if not env["pkg"]:
                    raise ValueError
            except ValueError:
                puts(red("Still no package name specified!!"))
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
                    if 'SLES' or 'SUSE Linux' in osname:
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
	    return 0

#############################################
# author: cedric.bleschet@inserm.fr (2015)
# La routine install_pkg permet d'installer un paquet
# Si le nom du paquet n est pas passe en argument, il le demande
##############################################
@task
def update_pkg(*pkg):
    """ Routine pour la mise a jour d\'un ou plusieurs paquets. Elle prend en argument une liste de paquets.
    Si rien n'est saisie comme argument, elle redemande un nom de paquet"""
    osname = '' # Systeme d'exploitation de la machine cible
    update_result = '' # Variable utilise pour stocker le texte lors d'une mise a jour   
    
    # Verification du nom de paquet
    try:
        if pkg:
            env["pkg"] = pkg
        else:
            raise ValueError
    except ValueError:
        try:
            env["pkg"] = prompt("Which packet should be updated?")
            if not env["pkg"]:
                raise ValueError
        except ValueError:
            puts(red("No package name!!"))
            return 1
    #Connexion au serveur et mis en jour du paquet en fonction de la distribution (SLES ou RHEL)
    try:
        osname = distrib_id()
        assert osname is not None
        with hide('status','aborts','stdout','warnings','running','stderr'):
            # Pour SLES
            if 'SLES' in osname:
                try:
                    sudo ("zypper --non-interactive refresh")
                    for packet in env["pkg"]:
                        update_result = sudo("zypper --non-interactive update " + packet)
                        if (update_result.find("Error") == -1) & (update_result.find("error") == -1):                           
                            puts(green("The package %s has been updated on the SLES server %s" % (packet,env.host)))
                        else: 
                            puts(red("An error occured during the update of %s on %s" % (packet,env.host)))
                            return 2
                except SystemExit:
                    puts(red("An error occured during while trying to update the SLES server %s" % env.host))

            # Pour Redhat
            elif osname in ['RedHatEnterpriseServer','RedHatEnterpriseES','RedHatEnterpriseAS','CentOS']:
                try:
                    sudo ("yum clean all")
                    for packet in env["pkg"]:
                        try:
                            sudo("yum update -y " + packet)
                        except SystemExit:
                            puts(red("An error occured during the update of %s a on %s" % (packet,env.host)))
                        else:
                            puts(green("%s has been updated on the server %s" % (packet,env.host))) 
                except SystemExit:
                    puts(red("An error occured while trying to update information on the deposite on the RHEL server %s" % env.host))
            else: 
                puts(red("An error occured during the update of %s on the server %s" % (env["pkg"],env.host)))
                return 1
    except NetworkError as network_error:
        print(red("ERROR : %s" % (network_error)))


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

# https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Linux/5/html/Tuning_and_Optimizing_Red_Hat_Enterprise_Linux_for_Oracle_9i_and_10g_Databases/sect-Oracle_9i_and_10g_Tuning_Guide-Swap_Space-Checking_Swap_Space_Size_and_Usage.html
@task
def adjust_swap_usage(new_swap_size_arg=None):
    """ Adjust the SWAP size considering the SPV0033xx document. The size if calaculated in function of the amount of RAM. Memory sizes are given in Gio"""
    swap_size = -1
    tmp_new_swap_size = ""
    ram_size = -1
    swap_partition="/dev/mapper/rootvg-swaplv"

    try:
        swap_size = sudo("awk '$1 == \"SwapTotal:\" {print $2}' /proc/meminfo")
        ram_size = sudo("free -k | awk '$1==\"Mem:\" {print $2}'")

        puts("swap size : %s" % swap_size)

        sudo("swapoff %s" % swap_partition)
        sudo("lvresize %s -L %s" % (swap_partition, swap_size))
        sudo ("mkswap %s" %swap_partition)
        sudo("swapon %s" % swap_partition)

#        lvresize /dev/VolGroup00/LogVol01 -L 768M 
#        swapon /dev/VolGroup00/LogVol01

    except NetworkError as network_error:
        print(red("ERROR : %s" % (network_error)))
    

################################################
# author: cedric.bleschet@inserm.fr (2015)
# La routine check_mem_usage() se base sur le fichier /proc/*/status et sur le champs VmSwap ou VmSize
# pour determiner la consommation de memoire swap ou de la memoire totale  par process. Sur RHEL4 et 5,
# le champs VMSwap n'est pas disponible. On utilise alors le champs VmSize qui donne l'utilisation de la memoire
# virtuelle sur le serveur
##############################################
@task
def check_mem_usage(memory_type_arg=None, nbr_line=15):
    """Check the memory usage (FULL or SWAP) of a server. It takes the memory type in argument"""
    osname="" # Distribution sur laquelle est executee la routine
    rhel_version = "" # RHEL version
    sles_version = "" # SLES version
    result_script = "" # Script to check memory usage execution result
    script_local_file="swap.sh" # local location of the BASH script to check memory usage
    script_remote_file="/tmp/swap.sh" #distant location of the BASH script
    memory_type="" # Get the memory type (FULL or SWAP)
    send_script=[] # Variable to check the status of the script sending

    # Check the memory type in argument (must be FULL or SWAP)
    try:
        if (memory_type_arg == "FULL") or (memory_type_arg == "SWAP"):
            memory_type = memory_type_arg
        else:
            raise ValueError
    except ValueError:
        try:
            memory_type = prompt("Which type of memory should be checked (FULL or SWAP)?")
            if (memory_type != "FULL") and (memory_type != "SWAP"):
                raise ValueError
        except ValueError:
            puts(red("Could not determine the memory type! just exit"))
            return 1

    with hide('status','aborts','stdout','warnings','running','stderr'):
        try :
            # Send the script "script_local_file" to the remote server in script_remote_file
            print(yellow("The following command may take a while (until 2 minutes...)"))
            send_script = put(script_local_file, script_remote_file, use_sudo=True, mode=0755)
            if send_script.failed:
                print(red("Could not send the check memory script on %s!" % env.host))
                return 2

            # If it is the full memory usage by process  we want to check
            # call the distant script with the arg VmSize to check the memory usage (SWAP +RAM)
            if memory_type == "FULL":
                try:
                    result_script = sudo(script_remote_file + "  -m VmSize -l " + str(nbr_line))
                    print("The eager processes in memory on %s are : " %env.host)
                except:
                    puts(red("An error occured during the procesing of the check memory script on %s!" % env.host))
            # If it is the SWAP memory we want to check
            # call the distant script with the arg VmSize to check the memory usage if no other information is available (old SLES andRHEL)
            # call the distant script with the arg VmSwap to check SWAP
            elif memory_type == "SWAP":
                osname = distrib_id()
                if 'SLES' or 'SUSE Linux' in osname:
                    sles_version = find_os_distro_cbl()
                    if sles_version == "sles11SP1":
                        try:
                            result_script = sudo(script_remote_file + "  -m VmSize -l " + str(nbr_line))
                            print(magenta(("Can not check swap memory on sles11 sp1, will display the memory usage instead")))
                            print("The eager processes in memory on %s are : " %env.host)
                        except:
                            puts(red("An error occured during the procesing of the check memory script on the SLES SP1 server %s!" % env.host))
                            return 3
                    else:
                        try:
                            result_script = sudo(script_remote_file + "  -m VmSwap -l " + str(nbr_line))
                            print("The eager processes in SWAP memory on %s are :" %env.host)
                        except:
                            print(red("An error occured during the procesing of the check memory script on the SLES server %s!" % env.host))
                            return 3

                elif osname in ['RedHatEnterpriseServer','RedHatEnterpriseES','RedHatEnterpriseAS','CentOS']:
                    rhel_version=find_os_distro_cbl()
                    if rhel_version == "redhat4" or rhel_version == "redhat5":
                        try:
                            result_script = sudo(script_remote_file + "  -m VmSize -l " + str(nbr_line))
                            print(magenta(("Can not check swap memory on RHEL4 or RHEL5, will display the memory usage instead")))
                            print("The eager processes in memory on %s are : " %env.host)
                        except:
                            print(red("An error occured during the procesing of the check memory script on the RHEL4 or RHEL5 server %s!" % env.host))
                            return 3
                    elif rhel_version == "redhat6" or rhel_version == "redhat7":
                        try:
                            result_script = sudo(script_remote_file + "  -m VmSwap -l " + str(nbr_line))
                            print("The eager processes in SWAP memory on %s are :" %env.host)
                        except:
                            print(red("An error occured during the procesing of the check memory script on the RHEL6 or 7 server %s!" % env.host))
                            return 3
                    else:
                        print(red("Could not recognized the RHEL version used!!"))
                        return 4
                else:
                    print(red("Could not recognized the linux distribution used"))
                    return 4
            else:
                    print(red("Incorrect script argument"))
                    return 5
            # Display the result of the script
            print("--------------------------------------------------")
            print("Nom             |PID    |User        |Memory in KB")
            print("--------------------------------------------------")
            print(result_script)
            print("--------------------------------------------------")
            # Delete the distant script
            sudo("rm -f " + script_remote_file)
            print(green("check_mem_usage finished in success on server %s" % env.host))
            
        except NetworkError as network_error:
            print(red("ERROR : %s" % (network_error)))
            
################################################
# author: cedric.bleschet@inserm.fr (2015)
# La routine bash_custom() 
##############################################
@task
def bash_custom():
    profile = "profile.txt" # Path to the section that should be added in the server's /etc/profile'
    content = "" # A string with the content of profile.txt file
    content2 = "" # A string with the content of bashrc.txt file
    server_profile = "/etc/profile" # Server Path to profile file
    bashrc = "bashrc.txt" # Path to the section that should be added in the server's bashrc'
    server_bashrc = "" # Server Path to bashrc file (unknown yet)
    osname = "" # Server OS (SLES or RHEL)

    # Test network connection to the targeted server
    try:
        with hide('status','aborts','stdout','warnings','running','stderr'):
            # Read the file profile and put it in the string content
            try:
                with open(profile) as file_des:
                    content = file_des.read()
            except IOError:
                print (red("Error: can\'t find file %s or read data") %profile)
                return 1
            else:
                # Add the string content into /etc/profile
                try:
                    fabric.contrib.files.append(server_profile, content, use_sudo=True)
                except:
                    print(red("Could not add customisation to the file : %s !! on %s " % (server_profile, env.host)))
                    return 2
            # Set the server_bashrc in function of the distribution
            try:
                osname = distrib_id()
                print(blue("the OS detected is %s" % osname))
                if osname in ['SLES', 'SUSE Linux']:
                    server_bashrc = "/etc/bash.bashrc"
                elif osname in ['RedHatEnterpriseServer','RedHatEnterpriseES','RedHatEnterpriseAS','CentOS']:
                    server_bashrc = "/etc/bashrc"
                else:
                    print(red("Could not recognized the OS version used : %s !!" % osname))
                    return 3
            except: 
                print(red("An error occured !!" % osname))
                return 3
            # Read the file bashrc and put it in the string content2
            try:
                with open(bashrc) as file_des:
                    content2 = file_des.read()
            except IOError:
                print (red("Error: can\'t find file %s or read data") %bashrc)
                return 4
            else:
                #add content to bashrc (rhel) or bash.bashrc (sles)
                try:
                    fabric.contrib.files.append(server_bashrc, content2, use_sudo=True)
                except:
                    print(red("Could not add customisation to the file : %s !! on %s " % (server_profile, env.host)))
                    return 5
            # Configure .bash_history
            try:
                sudo("mkdir -p /home/sys-infoger/Scripts/archive_history/")
                sudo("touch /home/sys-infoger/Scripts/archive_history/.bash_history")
                sudo("chmod 666 /home/sys-infoger/Scripts/archive_history/.bash_history")
                sudo("chmod +x /home/sys-infoger/")
            except:
                print(red("Could not configure bash_history") %bashrc)
                return 6
            print(green("bash_custom finished in success on server %s" % env.host))
    except NetworkError as network_error:
            print(red("ERROR : %s" % (network_error)))

################################################
# author: cedric.bleschet@inserm.fr (05/26/2015)
# The script check_pam_sshaccess() attempts to detect if the ssh access is restricted
# via a PAM module. To do so it looks in the file pam_file which is set to "etc/pam.d/sshd"
# by default and looks for the string pam_access.so
# Argument : pam_file = Location of the PAM file for ssh (/etc/pam.d/sshd by default)
# Return Value : A boolean which indicates whether or not the PAM module is activated
##############################################
@task
def check_pam_sshaccess(pam_file = "/etc/pam.d/sshd"):
    """Check the activation of the PAM module to restrict ssh access (access.conf)"""
    researched_string = "pam_access.so" # The string researched in the pam_file 
    check_pam_return = False # The return value of this script 
    pam_content = "" # Content of the PAM file

    # Check the network access to the server
    try:
        with hide('status','aborts','stdout','warnings','running','stderr'):
            # Try to read the file pam_file and put its content into pam_content
            try:
                pam_content = file_read(pam_file)
            except:
                print(red("Could not read %s" % (pam_file)))
                return -1
            #Look for the researched_string in pam_content. -1 means not found
            if pam_content.find(researched_string) == -1:
                print(red("Error : String %s not found in %s" \
                    % (researched_string, pam_file)))
                check_pam_return = False
            else:
                print(green("String %s found in %s" % (researched_string, pam_file)))
                check_pam_return = True
    except NetworkError as network_error:
            print(red("ERROR : %s" % (network_error)))
    return(check_pam_return)

@task
def detect_part(device = "/dev/sdb"):
    """Function to list the patitions used in /dev/sdb"""
    fstab_file = "/etc/fstab"
    fstab_list = []
    appli_vg = "applivg"

    try:
        with hide('status','aborts','stdout','warnings','running','stderr'):
            # Vérifier si /dev/sdb existe
            # Si oui vérifier le type de /dev/sdb (BTRFS ou LVM)
            fstab_content = file_read(fstab_file)
            fstab_list = fstab_content.split("\n")
            print(fstab_list)

    except NetworkError as network_error:
            print(red("ERROR : %s" % (network_error)))
@task
def create_user(name = None, role = None):
    """Add user on the hostname, add group staff if not created, add the target user to staff group.

    Keyword arguments:
    name -- (string) name of the user which will be created on the target
    role -- (string) user role : nominative = real name or name used by SSHGate (Ex cpiapg)
                                 software = named used to control the software or database FS
    Author: romain.dagnelie@inserm.fr
            updated by cedric.bleschet
    History: 2015 - Creation
             05/26/2015 - PAM, access.conf and add user role
    """
    user_result = "" # Variable used to check how the user was created
    user_list = [] # List used to check if the user already exists
    passwd_content = "" # Content of the "/etc/passwd" on the server 
    pwd_file = "/etc/passwd" # Full path to the file which manages users
    access_file = "/etc/access.conf" # Full path to the list of user authorized 
                                     # to connect via SSH
    last_access_line = "-:ALL:ALL EXCEPT LOCAL" # Last line of the access.conf 
                                                #file
    access_content = "" # String with the access.conf content 
    new_access_line = "" # Line to add in the access.conf file
    encrypted_passwd = "$6$.sZSzpsA$CtlJLDOkIJrABp8Tc4c1moFV0P3Hqe/u1YAf1csSbr6notlQPtCVYBKTKme5gm8d1VTO7QAiWMmWQlvARVva8/"

    try:
        with hide('status','aborts','stdout','warnings','running','stderr'):
            #Get the arguments
            if name is None :
                name = raw_input("Enter the user name :")
            if role is None :
                role = raw_input("Enter the role of the user \
                    (nominative or software):")
            
            #Get argument confirmation
            print(yellow("The arguments are name = %s and role = %s") \
                % (name, role))
            answer = raw_input("Is it correct? (y/n):")
            if answer != "y":
                print("Script interrupted by user")
                return 1

            #Check if the user has not been already created
            passwd_content = file_read(pwd_file)
            # import re : use of findall because it requires an exact match 
            user_list = re.findall('\\b'+name+'\\b', passwd_content)
            # If the length of user_list is bigger than 0, it means that the 
            # user already exists
            if len(user_list) > 0:
                user_result = sudo("grep %s /etc/passwd" % name)
                print(yellow("The user %s already exists : \n%s") \
                    % (name, user_result))
                return 2
            #Create user and group in function of its role
            if(role == "nominative"):
                try:
                    group_ensure('staff')
                    user_ensure(name)
                    group_user_ensure('staff', name)
                except:
                    print(red("Error during user creation!"))
                    return 3
                else:
                    user_result = sudo("grep %s /etc/passwd" % name)
                    print(green("User created : \n%s") % user_result)
                # If the ssh PAM module is set, it reads the file 
                # "/etc/access.conf", replaces the line "-:ALL:ALL EXCEPT LOCAL" 
                # of this file by a line corresponding to the newly created user
                # and finally add the line "-:ALL:ALL EXCEPT LOCAL" at the end 
                # of the file.
                if check_pam_sshaccess():
                    new_access_line = "+:"+name+":ALL"
                    try:
                        access_content = file_read(access_file)
                        file_update(access_file, \
                            lambda access_content:access_content.replace\
                            (last_access_line,new_access_line))
                        fabric.contrib.files.append(access_file, \
                            last_access_line, use_sudo=True, partial=False)
                    except:
                        print(red("Can not update %s " % access_file))
                        return 3
                # Set the password 
                user_passwd(name, encrypted_passwd, encrypted_passwd=True)
            elif(role == "software"):
                group_ensure(name)
                user_ensure(name)
                group_user_ensure(name, name)
            else:
                print(red("Error: Incorrect role given in argument, just exit"))
                return 2

    except NetworkError as network_error:
            print(red("ERROR : %s" % (network_error)))

