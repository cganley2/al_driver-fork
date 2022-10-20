# Global (python) modules

import glob # Warning: glob is unsorted... set my_list = sorted(glob.glob(<str>)) if sorting needed
import os

# Localmodules

import helpers

######
# NOTE: Implementation is based on VASP 5.4.1
######

def cleanup_and_setup(*argv, **kwargs):

    """ 
    
    Removes VASP-X folders, if they exist in the build_dir.
    
    Usage: cleanup_and_setup(<arguments>)
    
    Notes: See function definition in helpers.py for a full list of options. 
           Expects to be run from ALC-X folder
           Should only be run once per ALC
               
    """
    
    ################################
    # 0. Set up an argument parser
    ################################
    
    ### ...argv
    
    args_targets   = argv[0] # This is a pointer!
    args_this_case = -1
    
    if len(argv) == 2:
        args_this_case = argv[1]

    ### ...kwargs
    
    default_keys   = [""]*1
    default_values = [""]*1

    # VASP specific controls

    default_keys[0 ] = "build_dir"        ; default_values[0 ] = "."

    args = dict(list(zip(default_keys, default_values)))
    args.update(kwargs)    

    for i in args_targets: # 20 all
    
        if args_this_case == -1:
    
            for i in args_targets: # 20 all

                vasp_dir = args["build_dir"] + "/VASP-" + i
            
                if os.path.isdir(vasp_dir):
            
                    helpers.run_bash_cmnd("rm -rf " + vasp_dir)
                    helpers.run_bash_cmnd("mkdir  " + vasp_dir)
                                
                else:
                    helpers.run_bash_cmnd("mkdir  " + vasp_dir)
                
            return

    for i in args_targets: # 20 all
    
        if (i == "all") and (int(args_this_case) > 0):
            continue    

        vasp_dir = args["build_dir"] + "/VASP-" + i
        
        if os.path.isdir(vasp_dir):
        
            helpers.run_bash_cmnd("rm -rf " + vasp_dir + "/*")

            vasp_dir = args["build_dir"] + "/VASP-" + i + "/CASE-" + repr(args_this_case)

            if os.path.isdir(vasp_dir):
                helpers.run_bash_cmnd("rm -rf " + vasp_dir + "/*")
            else:
                helpers.run_bash_cmnd("mkdir  -p " + vasp_dir)
            
        else:
            helpers.run_bash_cmnd("mkdir -p  " + vasp_dir + "/CASE-" + repr(args_this_case))


def continue_job(*argv, **kwargs):

    """ 
    
    Checks whether all VASP single point calculations ran, resubmits if needed.
    
    Usage: continue_job(<arguments>)
    
    Notes: See function definition in vasp_driver.py for a full list of options. 
           Returns a SLURM jobid list
               
    """
    
    ################################
    # 0. Set up an argument parser
    ################################
    
    ### ...argv
    
    args_targets = argv[0] # This is a pointer!
    
    args_case    = 0
    
    if len(argv) == 2:
        args_case    = argv[1]
    
    ### ...kwargs
    
    default_keys   = [""]*1
    default_values = [""]*1
    
    default_keys[0 ] = "job_system"    ; default_values[0 ] = "slurm"              # slurm or torque       
    
    args = dict(list(zip(default_keys, default_values)))
    args.update(kwargs)    
    
    
    ################################
    # 1. Check on job status, resubmit if needed
    ################################    
    
    print("")
    print("    Attempting to continue VASP jobs for case: ", args_case)
    
    job_list = []
    
    for i in range(len(args_targets)): # 20 all
    
        if (args_targets[i] == "all") and (int(args_case) > 0):
            continue    
    
        CASE_PATH = "CASE-" + repr(args_case)
    
        if os.path.isdir("VASP-" + args_targets[i] + "/" + CASE_PATH):
        
            os.chdir("VASP-" + args_targets[i] + "/" + CASE_PATH)

            # Count the number of possible jobs
            
            count_POSCAR = len(glob.glob("*.in")) 
            
            # Count the number of completed jobs
            
            list_OUTCAR = glob.glob("*.out")
            count_OUTCAR = len(list_OUTCAR)

            for outfile in list_OUTCAR:
                with open(outfile, 'r') as f:
                    lines = f.readlines()
                f.close()
                result = next((True for line in lines if 'convergence has been achieved' in line), False)
                if not result:
                    count_OUTCAR -= 1

            print("")
            print("        Counted POSCAR:", count_POSCAR)
            print("        Counted OUTCAR:", count_OUTCAR)
            
            
            
            # If all jobs haven't completed, resubmit
            
            if count_POSCAR > count_OUTCAR:
            
                print("            Resubmitting.")

                if args["job_system"] == "slurm":
                    job_list.append(helpers.run_bash_cmnd("sbatch run_vasp.cmd").split()[-1])
                else:    
                    job_list.append(helpers.run_bash_cmnd("qsub run_vasp.cmd").replace('\n', ''))

            else:
                print("            Not resubmitting.")
            
            print("")
            
            os.chdir("../..")
        else:
            print("Cant find directory VASP-"+ args_targets[i] + "/" + CASE_PATH)
            print(helpers.run_bash_cmnd("pwd"))

    return job_list    
    

def check_convergence(my_ALC, *argv, **kwargs):

    """
    
    Checks whether vasp jobs have completed within their requested NELM
    
    Usage: check_convergence(my_ALC, no. cases, VASP_job_types)
    
    Notes: VASP_job_types can be ["all"], ["all","20"] or ["20"]
           
    WARNING: Deletes OUTCARs, modifies *.INCARS
    
    """
    
    # Developer notes: vasp_driver.continue_job counts *.POSCARS and *.OUTCARS.
    # If !=, then simply resubs the .cmd file and lets the .cmd file take care 
    # of the rest of the logic. The .cmd file also looks to see if *.OUTCAR 
    # exists. If it does, it skips the job. otherwise, copies 
    # <temperature>.incar to incar and builds the corresponding POTCAR
    #
    # So what this function does is  delete the corresponding .OUTCARS, and then 
    # edits all .INCAR's to have IALGO = 38
    #
    # Once run, should just be able to call vasp_driver.continue_job as normally
    # done in main.py        

    
    ################################
    # 0. Set up an argument parser
    ################################
    
    ### ...argv

    args_cases   = argv[0]    
    args_targets = argv[1] # ... all ... 20


    # VASP specific controls
    
    # ...

    # Overall job controls    
    
    # ...
    
    #print helpers.run_bash_cmnd("pwd")
    
    #os.chdir("ALC-" + `my_ALC`)
    
    total_failed = 0
    
    
    ################################
    # Generate a list of all VASP jobs with n-SC >= NELM
    ################################

    for i in range(len(args_targets)): # 20 all

        if not os.path.isdir("VASP-" + args_targets[i]):
    
            print("Skipping VASP-" + args_targets[i])
        
            continue

        
        print("Working on:","VASP-" + args_targets[i])
    
        os.chdir("VASP-" + args_targets[i])
        
        # Clear out the "tries" file so we try to achieve convergence one more time

        helpers.run_bash_cmnd("rm -f *.tries")
        
        # Build the list of failed jobs for the current VASP job type (i.e. "all" or "20")
    
        base_list = []
        base_case = []
        
        for j in range(args_cases):
        
                tmp_list = sorted(glob.glob("CASE-" + repr(j) + "/*.out")) # list of all .outcar files for the current ALC's VASP-20 or VASP-all specific t/p case
                
                for k in range(len(tmp_list)):
                            
                    # Get max NELM
                
                    NELM = None
                
                    with open(tmp_list[k]) as ifstream:
                    
                        for line in ifstream:
                            
                            if "convergence NOT achieved" in line:
                            
                                NELM = int(line.split()[4])
                                print("In case" + j + "convergence was not achieved: " + line)
                                break

                    ifstream.close()
                                
                    # Determine if job failed because NELM reached
                
                    oszicar = '.'.join(tmp_list[k].split('.')[:-1]) + ".OSZICAR"
                    last_rmm = int(helpers.tail(oszicar,2)[0].split()[1])
                
                    #print last_rmm, NELM
                    
                    if last_rmm >= NELM:
                        base_list.append('.'.join(tmp_list[k].split('.')[:-1])) # Won't include the final extension (e.g. POSCAR, OSZICAR, OUTCAR, etc)
                        base_case.append(int(tmp_list[k].split('.')[0].split('_')[-1]))
                    
        
        print("Found",len(base_list),"incomplete jobs")
        
        if len(base_list) == 0:
            os.chdir("..")
            continue
        
        total_failed += len(base_list)
        
        # Delete corresponding .OUTCAR files
        
        for j in range(len(base_list)):
            helpers.run_bash_cmnd("rm -f " + base_list[j] + ".out")
            
        # Update the *.INCAR files for the cases
        
        #print helpers.run_bash_cmnd("pwd")
        
        incars = []

        for j in base_case: # Only update INCARs for failed cases
            incars += glob.glob("CASE-" + repr(j) + "/*.in")
    
        for j in range(len(incars)):
        
            print("Working on:",incars[j])
            
            if os.path.exists(incars[j] + ".bck"):
                helpers.run_bash_cmnd("cp " + incars[j] + ".bck " + incars[j])
            
            helpers.run_bash_cmnd("cp " + incars[j] + " " + incars[j] + ".bck")
        
            contents = helpers.readlines(incars[j])
            
            # Get index of line containing "IALGO"
            
            targ = next(i for i, w in enumerate(contents) if "diagonalization" in w)
            line = contents[targ].split()
            
            # Make sure it contains the expected value, then replace with 38/Normal
            
            if "diagonalization" in line[0]:

                if line[2] != 'david':
                    print("ERROR: Expected diagonalization = 'david', got", line[2])
                    print("Would have replaced with cg")
                    exit()      
                line[2] = "cg"                                                        
            
            contents[targ] = ' '.join(line)+'\n'
    
            helpers.writelines(incars[j],contents)
            
            #print "\tFile",incars[j],"updated"

        os.chdir("..")
    #os.chdir("..")
    
    return  total_failed

def generate_qe_infile(inxyz, *argv):

    """ 
    
    Converts a .xyz file to a QE input file.
    
    Usage: (my_file./usr/workspace/wsb/rlindsey/AL_Driver_SVN/rlindsey_branch/xyz, ["C","O"], 6500) # , [1,2])
    
    Notes: The second argument is list of atom types
           The final argument is the smearing temperature, in Kelvin
              
    WARNING: Assumes the inxyz comment line is formatted like:
             <boxl_x> <boxl_y> <boxl_z> .....
         or
         NON_ORTHO <a_x> <a_y> <a_z> <b_x> <b_y> <b_z> <c_x> <c_y> <c_z> ...

    """

    atm_types = argv[0] # pointer!
    smearing  = int(argv[1])
    ifstream = open(inxyz,'r')
    ofstream = open(inxyz + ".in", 'w')

    qe_in_skel = open(glob.glob(args["basefile_dir"] + 'qe_in_skel.in', 'r')).readlines()
    
    
    # Set up the header portion

    nat = ifstream.readline().split()[0]       # No. atoms (as a string)
    box = ifstream.readline().split()   # Box lengths
    
    # Count up the number of atoms of each type
    
    contents = ifstream.readlines()
    contents.sort() # Vasp expects sorted coordinates
    
    natm_types = [0]*len(atm_types)
    
    for i in range(len(contents)):
    
        for j in range(len(atm_types)):
            
            if atm_types[j] in contents[i]:
                
                natm_types[j] += 1
                
    
    # Remove any elements that don't appear in the coordinate file
    # But first, make sure everything is sorted 
    
    tmp = zip(atm_types,natm_types)
    tmp.sort() # Sorts by the first entry (atom types) ... alphabetical
    
    for i in range(len(tmp)-1,-1,-1): # Goes through list backwards
        
        if tmp[i][1] == 0: 
        
            tmp.pop(i)
    
    atm_types  = list(zip(*tmp)[0])
    natm_types = map(str, list(zip(*tmp)[1]))
    
    substitution_list = [
                            ['@NTYP@', natm_types],
                            ['@NAT@', len(contents)]
                        ] #really underwhelming at this point

    sub = dict(substitution_list)

    for key, val in sub.items():
        for idx, ele in enumerate(qe_in_skel):
            if key in ele:
                qe_in_skel[idx] = ele.replace(key, val)

    for line in qe_in_skel:
        print('Writing qe_in_skel lines to ' + ofstream)
        ofstream.write(line)

    # Finish up the header portion

    ofstream.write('CELL_PARAMETERS {angstrom}\n')
    
    if box[0] == "NON_ORTHO":
        ofstream.write(box[1] + " " +  box[2] + " " +  box[3] + '\n')
        ofstream.write(box[4] + " " +  box[5] + " " +  box[6] + '\n')
        ofstream.write(box[7] + " " +  box[8] + " " +  box[9] + '\n')
    else:
        ofstream.write(box[0] + " 0.000       0.000" + '\n')
        ofstream.write("0.000 " + box[1]  + " 0.000" + '\n')
        ofstream.write("0.000     0.000 " +   box[2] + '\n')
    
    ofstream.write('ATOMIC_POSITIONS {angstrom}\n')
    
    for i in range(len(contents)):

        ofstream.write(line[i])
        
    ofstream.close()


def post_process(*argv, **kwargs):

    """ 
    
    Converts a converts a VASP OUTCAR file to .xyzf file
    
    Usage: post_process(<arguments>)
    
    Notes: See function definition in vasp_driver.py for a full list of options. 
               
    """
    
    ################################
    # 0. Set up an argument parser
    ################################
    
    ### ...argv
    
    args_targets    = argv[0] # ... all ... 20
    args_properties = argv[1] # "ENERGY STRESS" ...etc for the post process script
    
    args_cases    = 1
    
    if len(argv) == 3:
        args_cases    = argv[2]    
    
    
    ### ...kwargs
    
    default_keys   = [""]*1
    default_values = [""]*1


    # VASP specific controls
    
    default_keys[0 ] = "vasp_postproc"  ; default_values[0 ] = ""        # POTCAR, KPOINTS, and INCAR    

    args = dict(list(zip(default_keys, default_values)))
    args.update(kwargs)    
    
    ################################

    for i in range(len(args_targets)): # 20 all

        if not os.path.isdir("VASP-" + args_targets[i]):
        
            print("Skipping VASP-" + args_targets[i])
            
            continue

            
        print("Working on:","VASP-" + args_targets[i])
    
        os.chdir("VASP-" + args_targets[i])
    
        # helpers.run_bash_cmnd("rm -f OUTCAR.xyzf")
        
        outcar_list = []
        
        for j in range(args_cases):
        
            outcar_list += sorted(glob.glob("CASE-" + repr(j) + "/*.out"))
            
        for j in range(len(outcar_list)):
        
            # Make sure the job completed within requested NELM
            
            
            # Get max NELM
                
            NELM = None
            
            with open(outcar_list[j]) as ifstream:
                
                for line in ifstream:
                        
                   if "convergence has been achieved" in line:
                        
                        NELM = int(line.split()[4])
                        print(outcar_list[j] + " has converged!")
                        break
            
            # Determine if job failed because NELM reached
            
            # oszicar = '.'.join(outcar_list[j].split('.')[:-1]) + ".OSZICAR"
            # last_rmm = int(helpers.tail(oszicar,2)[0].split()[1])
            
            # if last_rmm >= NELM:
                
            #     print("Warning: VASP job never converged within requested NELM", outcar_list[j], ":", NELM)
            #     continue            
            

            # print(helpers.run_bash_cmnd(args["vasp_postproc"] + " " + outcar_list[j] + " 1 " + args_properties + " | grep ERROR "))
            
                        
            
            # #print "Working on: ", outcar_list[j] # CASE-0/case_0.indep_0.traj_20F_#000.xyz.OUTCAR
            
            # # Figure out the temperature
            
            
            # tmpfile = ''.join(outcar_list[j].split("OUTCAR"))+"POSCAR"
            # tmp_temp =  helpers.head(tmpfile,1)[0].split()[-2]
            
            # tmpfile = outcar_list[j]
            # tmpfile = tmpfile + ".xyz.temps"
            # tmpstream = open(tmpfile,'w')
            # tmpstream.write(tmp_temp + '\n')
            # tmpstream.close()        
            
            # # Make sure the configuration energy is less than or equal to zero
            
            # if "ENERGY" in args_properties:
            
            #     tmp_ener = helpers.head(outcar_list[j] + ".xyzf",2)
            #     tmp_ener = float(tmp_ener[1].split()[-1])
                
            #     if tmp_ener >= 0.0:
                    
            #         print("Warning: VASP energy is positive energy for job name", outcar_list[j], ":", tmp_ener, "...skipping.")
            #         continue
            
            # if os.path.isfile(outcar_list[j] + ".xyzf"):
            
            #     if os.path.isfile("OUTCAR.xyzf"):
            
            #         helpers.cat_specific("tmp.dat", ["OUTCAR.xyzf", outcar_list[j] + ".xyzf"])
            #         helpers.cat_specific("tmp.tmp", ["OUTCAR.temps", tmpfile])                    
            #     else:
            #         helpers.cat_specific("tmp.dat", [outcar_list[j] + ".xyzf"])
            #         helpers.cat_specific("tmp.tmp", [tmpfile])                    
                
            #     helpers.run_bash_cmnd("mv tmp.dat OUTCAR.xyzf")
            #     helpers.run_bash_cmnd("mv tmp.tmp OUTCAR.temps")
                
        
        os.chdir("..")

def setup_vasp(my_ALC, *argv, **kwargs):

    """ 
    
    Sets up and launches VASP single point calculations
    
    Usage: setup_vasp(1, <arguments>)
    
    Notes: See function definition in vasp_driver.py for a full list of options. 
           Expects to be run from the ALC-X folder.
           Expects the "all" file in the ALC-X folder.
           Expects the "20" file in the ALC-X/INDEP_X folder.
           Requries a list of atom types.
           Expects a potcar file for each possible atom type, named like:
                  X.POSCAR
           All other input files (INCAR, KPOINTS, etc) are taken from config.VASP_FILES.
           Returns a SLURM jobid
           
    WARNING: For ALC-0, smearing is taken to be the corresponding temeprature
             in the traj_list.dat file.
    
    WARNING: For ALC-1+, smearing is a specified parameter.    
    
    WARNING: Largely only intended for liquids, so far.    
              
    """
    
    ################################
    # 0. Set up an argument parser
    ################################
    
    ### ...argv
    
    args_targets = argv[0] # This is a pointer!
    atm_types    = argv[1]
    my_case      = ""
    
    if len(argv) >= 3:
        my_case = str(argv[2])
    
    my_smear = "TRAJ_LIST"
        
    if len(argv) >= 4:
        my_smear = str(argv[3])
    
    
    ### ...kwargs
    
    default_keys   = [""]*14
    default_values = [""]*14


    # VASP specific controls
    
    default_keys[0 ] = "basefile_dir"  ; default_values[0 ] = "../VASP_BASEFILES/"  # POTCAR, KPOINTS, and INCAR
    default_keys[1 ] = "traj_list"        ; default_values[1 ] = "traj_list.dat"    # Traj_list used in fm_setup.in... last column is target temperatura
    default_keys[2 ] = "modules"        ; default_values[2 ] = "qe/7.0"                # Post_proc_lsq*py file... should also include the python command
    default_keys[3 ] = "build_dir"        ; default_values[3 ] = "."                # Post_proc_lsq*py file... should also include the python command
    default_keys[4 ] = "first_run"     ; default_values[4 ] = False                 # Optional... is this the first run? if so, dont search for "CASE" in the name


    # Overall job controls    
    
    default_keys[5 ] = "job_nodes"     ; default_values[5 ] = "1"                   # Number of nodes for ChIMES md job
    default_keys[6 ] = "job_ppn"       ; default_values[6 ] = "24"                  # Number of processors per node for ChIMES md job
    default_keys[7 ] = "job_walltime"  ; default_values[7 ] = "1"                   # Walltime in hours for ChIMES md job
    default_keys[8 ] = "job_queue"     ; default_values[8 ] = "defq"              # Queue for ChIMES md job
    default_keys[9 ] = "job_account"   ; default_values[9 ] = "pclancy3"             # Account for ChIMES md job
    default_keys[10] = "job_executable"; default_values[10] = ""                    # Full path to executable for ChIMES md job
    default_keys[11] = "job_system"    ; default_values[11] = "slurm"               # slurm or torque       
    default_keys[12] = "job_file"       ; default_values[12] = "run.cmd"            # Name of the resulting submit script   
    default_keys[13] = "job_email"     ; default_values[13] = True                  # Send slurm emails?
    

    args = dict(list(zip(default_keys, default_values)))
    args.update(kwargs)    
    
    
    run_vasp_jobid = []
    
    ################################
    # 1. Set up and launch the vasp single point calculations
    ################################
        
    for i in range(len(args_targets)): # 20 all
    
        if (args_targets[i] == "all") and (int(my_case) > 0):
            continue    
    
        curr_dir = helpers.run_bash_cmnd("pwd").rstrip() # This should be either CASE-X... (ALC>=1) or ...? (ALC==0)
    
        vasp_dir = "VASP-" + args_targets[i] + "/CASE-" + my_case
        
        helpers.run_bash_cmnd("mkdir -p " + vasp_dir)        
            
        # Set up an launch the job
        
        os.chdir(vasp_dir)
        
        # Prepare for the case where smearing is read from traj_list file
        
        temps = None
        
        if my_smear == "TRAJ_LIST":

            # Need to figure out the possible temperatures ... 
            
            ifstream = ""
            
            try:
                ifstream = open("../../../ALC-0/GEN_FF/" + args["traj_list"], 'r')
            except:
                ifstream = open("../../../ALC-1/GEN_FF/" + args["traj_list"], 'r')
                

            temps    = ifstream.readlines()[1:]

            for j in range(len(temps)):
                temps[j] = temps[j].split()

            ifstream.close()
        
        if args_targets[i] == "20":
        
            my_md_path = curr_dir + "/CASE-" + str(my_case) + "_INDEP_0/" # ONLY EVER COMES FROM FIRST INDEP " + str(my_indep) + "/"

            my_file = "case_" + str(my_case) + ".indep_0.traj_" + args_targets[i] + "F.xyz"

            helpers.run_bash_cmnd("cp " + my_md_path + "/traj_20F.xyz " + my_file)
            
            atoms  = helpers.head(my_file,1)[0].rstrip()
            frames = helpers.wc_l(my_file  )
            frames = frames / (2+int(atoms))

            helpers.break_apart_xyz(frames, my_file)
            
            helpers.run_bash_cmnd("rm -f " + ' '.join(glob.glob("*FORCES*")))
            
            temp = my_smear

            # Generate the POSCAR files

            target_files = ' '.join(sorted(glob.glob("case_" + str(my_case) + ".indep_0.traj_" + args_targets[i] + "F_#*"))).split()

            for j in target_files:
            
                if my_smear == "TRAJ_LIST":

                    temp = int(temps[int(my_case)][2])
                    
                print("\tOn case",my_case,"configuration",j,"generating QE infile with smearing temperature:", temp)

                generate_qe_infile(j, atm_types, temp)    
                
        else:

            ifstream     = open(curr_dir + "/" + args_targets[i] + ".selection.dat", 'r') # all.selection.dat ... a list of indices
            target_files = ifstream.readlines()
            ifstream     .close()
            
            ifstream     = open(curr_dir + "/" + args_targets[i] + ".xyzlist.dat",   'r') # all.xyzlist.dat ... a list of file names
            contents     = ifstream.readlines()
            ifstream     .close()

            temp = my_smear

            for j in range(len(target_files)):

                sel_file = contents[int(target_files[j].rstrip())].split()
                sel_file = sel_file[len(sel_file)-1]
                
                case_check = "CASE-" + my_case
                
                if (not args["first_run"]) and (case_check not in sel_file):

                    continue

                if my_smear == "TRAJ_LIST":

                    for k in range(len(temps)):
    
                        if ("CASE-" + str(k) in sel_file) or (temps[k][2] in sel_file):
                    
                            temp = temps[k][2]

                            break
                            
                print("\tOn case",my_case,"configuration",sel_file,"generating POSCAR with smearing temperature:",temp)

                generate_qe_infile(curr_dir + "/" + sel_file, atm_types, temp)

                helpers.run_bash_cmnd("mv " + curr_dir + "/" + sel_file + ".POSCAR tmp.POSCAR")
                
    
                sel_POSCAR = sel_file + ".POSCAR"
                sel_POSCAR = sel_POSCAR.replace('/','.')
                
                helpers.run_bash_cmnd("mv  tmp.POSCAR " + sel_POSCAR)


        ################################
        # 2. Launch the actual job 
        ################################
    
        # Grab the necessary files
    
        helpers.run_bash_cmnd("cp " + ' '.join(glob.glob(args["basefile_dir"] + "/*")) + " .")
        
        # Delete any not for this case (temperature)

        # incars = sorted(glob.glob("*.INCAR"))
        
        # tag = glob.glob("*#*POSCAR")
        # tag = len(str(len(tag)))
        # tag = "".zfill(tag+1)

        # temp   = helpers.head(glob.glob("*" + tag + "*POSCAR")[0],1)[0].split()[-2]

        # incars.remove(temp +".INCAR")
        # helpers.run_bash_cmnd("rm -f " + ' '.join(incars))
    
        # Create the task string
                
        job_task = []
        job_task.append("module load " + args["modules"] + '\n')
    
    
        for k in range(len(atm_types)):
    
            job_task.append("ATOMS[" + repr(k) + "]=" + atm_types[k] + '\n')
    
        job_task.append("for j in $(ls *.in)")
        job_task.append("do")
        job_task.append("    TAG=${j%*.in}")
        job_task.append("    if grep -q \"convergence has been achieved\" ${TAG}.out; then")
        job_task.append("        continue")
        job_task.append("    fi")
        job_task.append("    prev_tries=`wc -l ${TAG}.tries`")
        job_task.append("    if [ $prev_tries -ge 2 ]; then")
        job_task.append("        continue")
        job_task.append("    fi")
        job_task.append("    echo \"Attempt\" >> ${TAG}.tries")
        job_task.append("srun -N " + repr(args["job_nodes" ]) + " -n " + repr(int(args["job_nodes"])*int(args["job_ppn"])) + " " + "/data/apps/extern/qe/7.0-gcc-9.3.0-openmpi-3.1.6/bin/pw.x" + " -inp ${TAG}.in > ${TAG}.out")
        job_task.append("done")
        
        this_jobid = helpers.create_and_launch_job(job_task,
            job_name       =          "vasp_spcalcs"  ,
            job_email      =     args["job_email"   ] ,            
            job_nodes      = str(args["job_nodes"    ]),
            job_ppn        = str(args["job_ppn"    ]),
            job_walltime   = str(args["job_walltime"]),
            job_queue      =     args["job_queue"    ] ,
            job_account    =     args["job_account" ] ,
            job_system     =     args["job_system"  ] ,
            job_file       =     "run_vasp.cmd")
            
        run_vasp_jobid.append(this_jobid.split()[0])    
    
        os.chdir(curr_dir)
    
    return run_vasp_jobid        
