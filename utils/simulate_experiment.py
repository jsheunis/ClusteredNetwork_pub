import os
abspath = os.path.split(os.path.abspath(__file__))[0]
import sys; 
from sim_nest import simulate as simulate_network
#from Helper import ClusterModelNEST
#from Defaults import defaultSimulate as default
import default
import analyse_nest
from copy import deepcopy
import numpy as np
import matplotlib.pyplot as plt
import pylab
from experiment import stimulus_protocol
import organiser
from general_func import *
#organiser.datapath = os.path.join(abspath,'chapters/monkey_model/data')
organiser.datapath = os.path.join(abspath,'data')

def simulate(original_params):

    params = deepcopy(original_params)
    if 'jipratio' in list(params.keys()):
        print('warning: jipratio is called jipfactor')
        params['jipfactor'] = params['jipratio']
    np.random.seed(params.get('randseed',None))
    pylab.seed(params.get('randseed',None))

    conditions = params['conditions']
    trials = params['trials']
    
    stimuli = [stimulus_protocol(condition,trials) for condition in conditions]

    clusters_per_direction = params.get('clusters_per_direction',1)

    
    all_clusters = np.arange(params['Q'])
    direction_clusters = []
    for direction in range(1,7):
        np.random.shuffle(all_clusters)
        direction_clusters.append(all_clusters[:clusters_per_direction])
        all_clusters = all_clusters[clusters_per_direction:]


    t = params.get('warmup',0)
    multi_stim_amps = [[0.] for i in range(6)]
    multi_stim_times = [[0.] for i in range(6)]
    trial_starts = []
    trial_types = []

    isi = params.get('isi',2000)
    isi_vari = params.get('isi_vari',500)
    ps_stim_amps = params['condition_stim_amps']
    rs_stim_amp = params['rs_stim_amp']
    prep_length = params.get('prep_length',1000)
    rs_length = params.get('rs_length',200)

    for i,condition in enumerate(conditions):
        for trial in range(trials):
            t += isi + np.int16(np.random.rand()*isi_vari)
            trial_starts.append(t)
            ps_directions = np.where(stimuli[i][trial,:,0])[0]
            rs_direction =  np.where(stimuli[i][trial,:,1])[0][0]
            trial_types.append((condition,rs_direction+1))
            
            # make the amplitudes for the preparatory period
            for ps_direction in ps_directions:
                multi_stim_times[ps_direction].append(t)
                multi_stim_amps[ps_direction].append(ps_stim_amps[i])

            t += prep_length
            for ps_direction in ps_directions:
                if ps_direction == rs_direction:
                    continue
                multi_stim_times[ps_direction].append(t)
                multi_stim_amps[ps_direction].append(0)

            # target stimulus
            t+=1
            multi_stim_times[rs_direction].append(t)
            multi_stim_amps[rs_direction].append(rs_stim_amp)
            t+= rs_length
            multi_stim_times[rs_direction].append(t)
            multi_stim_amps[rs_direction].append(0)
    
    multi_stim_amps =[ pylab.array(l) for l in multi_stim_amps]
    multi_stim_times =[ pylab.array(l) for l in multi_stim_times]



    if params.get('plot_stimuli',False):
        plt.figure()
        for i in range(6):
            plt.step(multi_stim_times[i], i*1.2*rs_stim_amp +multi_stim_amps[i],where  ='post')

        for ts in trial_starts:
            plt.axvline(ts,linestyle = '--',color = 'k')



    params['multi_stim_amps'] = multi_stim_amps
    params['multi_stim_times'] = multi_stim_times
    params['multi_stim_clusters'] = direction_clusters
            
    
    params['simtime'] = t+ 2*isi

    



    # set up clustering parameters
    jep = params['jep']
    jipfactor = params['jipfactor']
    jip = 1. +(jep-1)*jipfactor
    params['jplus'] = np.around(np.array([[jep,jip],[jip,jip]]),5)
    #EI_Network = ClusterModelNEST.ClusteredNetwork(default, params)
    # Creates object which creates the EI clustered network in NEST
    #result = EI_Network.get_simulation() 

    result = simulate_network(params)
    
    result['trial_starts'] = trial_starts
    result['trial_types'] = trial_types
    result['direction_clusters'] = direction_clusters
    
    # now take the spiketrians appart per condition, direciton and unit

    trial_spiketimes = analyse_nest.cut_trials(result['spiketimes'], result['trial_starts'], params['cut_window'])
    N_E =params.get('N_E',default.N_E) 
    unit_spiketimes = analyse_nest.split_unit_spiketimes(trial_spiketimes,N_E)
    
    trial_types = np.array(result['trial_types'])
    conditions = trial_types[:,0]
    directions = trial_types[:,1]
    trials = np.arange(len(directions))

    trial_directions = dict(list(zip(trials,directions)))
    trial_conditions = dict(list(zip(trials,conditions)))
    
    for u in list(unit_spiketimes.keys()):
        spiketimes = unit_spiketimes[u]
        directions = np.array([trial_directions[int(trial)] for trial in spiketimes[1]])
        conditions = np.array([trial_conditions[int(trial)] for trial in spiketimes[1]])
        #print spiketimes.shape,directions.shape

        spiketimes = np.append(spiketimes, directions[None,:],axis=0)
        spiketimes = np.append(spiketimes, conditions[None,:],axis=0)
        unit_spiketimes[u] = spiketimes

    result['unit_spiketimes'] = unit_spiketimes

    return result

    


def get_simulated_data(extra_params = {},datafile = 'simulated_data',
                        save = True,redo=False, backup_file = None):

    params = {'conditions':[1,2,3],'trials':150,'clusters_per_direction':1,'Q':20,
                'jep':4,'jipfactor':3/4.,'prep_length':1000,'rs_length':400,
                'isi':1500,'isi_vari':200,'condition_stim_amps':[0.1,0.1,0.1],
              'rs_stim_amp':0.1,'n_jobs':12,'cut_window':[-500,2000]}

    for k in list(extra_params.keys()):
        params[k] = extra_params[k]

    return organiser.check_and_execute(params, simulate, 
                datafile,save = save,
                backup_file = backup_file,redo=redo)








if __name__ == '__main__':
    # result = get_simulated_data({'randseed':1,'trials':2,
    #                 'N_E':1200,'N_I':300,'I_th_E':1.25,'I_th_I':0.78,
    #                 'Q':6,'jep':3.5,'condition_stim_amps':[0.,0.,0.],
    #                 'rs_stim_amp':0.,'simtime':1000},
    #                 datafile='test_simulate_experiment', save=False, redo=True)

    result = get_simulated_data({'randseed':8721,'trials':1,
                    'N_E':1200,'N_I':300,'I_th_E':1.25,'I_th_I':0.78,
                    'Q':6,'jep':3.2,'condition_stim_amps':[1.,1.,1.],
                    'rs_stim_amp':0.1,'simtime':1000,'conditions':[3]},
                    datafile='test_simulate_experiment', save=False, redo=True)





    plt.figure()
    spiketimes = result['spiketimes']
    plt.plot(spiketimes[0],spiketimes[1],'.k',ms = 0.5)
    plt.show()
