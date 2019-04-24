import os, sys
import numpy as np
import cv2 as cv 
# import multiprocessing as mp
from multiprocessing import Process
from collections import OrderedDict
import csv

def perform_train(data_path, cfg_path, pretrained_weight):
	# command_string = "./../darknet/ detector train ../data/gun.data ../cfg/yolov3_gun.cfg ../darknet53.conv.74 -gpus 1,2,3 -dont_show"
	command_string = "./../darknet detector train "+data_path+" "+cfg_path+" "+pretrained_weight+" -gpus 1,2,3 -dont_show"
	os.system(command_string)


def perform_inference(data_path, cfg_path, weight_path, weight_file):
	command_string = "./../darknet detector map "+data_path+" "+cfg_path+" "+weight_path+"/"+weight_file+" -gpus 0 -dont_show >> "+weight_file.split(".")[0]+".log"
	os.system(command_string)


if __name__ == "__main__": 
	#initialize dictionary for stopping condition with configuration parameters
	f = open('plot.conf','rb')
	line = f.readline()
	param_dict = OrderedDict()
	while(len(line)):
		# print(len(line))
		# print(line)
		line = line.split('\n')[0]
		# print(line)
		param_dict[line.split(' = ')[0]] = (line.split(' = ')[1])
		line = f.readline()
	# f.close()

	params_batch = np.float32( param_dict["BATCH_SIZE"] )
	params_sub_batch = np.float32( param_dict["SUB_BATCH_SIZE"] )
	params_min_epoch = np.float32( param_dict["MIN_EPOCH"] )
	params_max_epoch = np.float32( param_dict["MAX_EPOCH"] )
	params_min_delta = np.float32( param_dict["MIN_DELTA"] )
	params_patience = np.float32( param_dict["PATIENCE"] )
	params_gpu_indx = np.float32( param_dict["GPU_NUM"] )
	params_data_file = param_dict["DATA_FILE"]
	params_cfg_file = param_dict["CFG_FILE"]
	params_names_file = param_dict["NAMES_FILE"]
	params_backup_path = param_dict["BACKUP"]
	params_pretained_weight = param_dict["PRETRAINED"]
	# NEW conditions for new params
	all_map = np.array([])
	# baseline_map = -1
	best_map_iter = -1
	best_map = -1
	epoch_count_baseline = 0
	stop_flag = 0
	#Run train
	first_run = 1
	# perform_train( params_data_file, params_cfg_file, params_pretained_weight )
	p = Process(target = perform_train, args = (params_data_file, params_cfg_file, params_pretained_weight,))
	p.start()
	#Run test for mAP and F1 score with conditions for stop_flag
	# backup_path = "/home/anerudh/darknet/backup_guns2_test"
	while(True):
		if(first_run==1):
			count_backup_files = int( os.popen("ls "+params_backup_path+" -1 | wc -l").read()[:-1] )
			first_run = 0
			csv_filename = 'map_plots_early_stop.csv'
			f0 = open(csv_filename, 'a+')
			writ = csv.writer(f0, delimiter = ',')
			csv_write_list = []
			csv_write_list.append('weight')
			f1 = open(params_names_file)
			line = f1.readline()
			while(len(line)):
				csv_write_list.append( line.split('\n')[0] + '-AP' )
				line = f1.readline()
			csv_write_list.append('F1-score')
			csv_write_list.append('mAP')
			writ.writerow(csv_write_list)
			f0.close()
		elif( first_run==0 and count_backup_files < int(os.popen("ls "+params_backup_path+" -1 | wc -l").read()[:-1]) ):
			#new weight file create. Check mAP and stopping condition
			#
			count_backup_files = int( os.popen("ls "+params_backup_path+" -1 | wc -l").read()[:-1] )
			weight_file = sorted(os.popen("ls "+params_backup_path).read().split("\n"))[-1]
			
			#run inference here-
			perform_inference(params_data_file, params_cfg_file, params_backup_path, weight_file)
			
			csv_filename = 'map_plots_early_stop.csv'
			f0 = open(csv_filename, 'a+')
			writ = csv.writer(f0, delimiter = ',')
			# csv_write_list = []
			# csv_write_list.append(first_run)
			# csv_write_list.append(count_backup_files)
			# csv_write_list.append( int(os.popen("ls "+params_backup_path+" -1 | wc -l").read()[:-1]) )
			# writ.writerow(csv_write_list)


			f1 = open(params_names_file)
			line = f1.readline()
			csv_write_list = []
			csv_write_list.append( weight_file.split('.')[0].split("_")[-1] )
			while(len(line)):
				f2 = open(weight_file.split(".")[-2] +".log")
				line2 = f2.readline()
				while(len(line2)):
					if(line[:-1] in line2):
						csv_write_list.append( line2.split(" ")[line2.split(" ").index(line[:-1]+",") + 3] )
					line2 = f2.readline()
				line = f1.readline()
			f2 = open(weight_file.split(".")[-2] +".log")
			line2 = f2.readline()
			count = 0
			while(len(line2)):
				if("F1-score" in line2):
					csv_write_list.append( line2.split(" ")[line2.split(" ").index("F1-score") + 2] )
				if("mAP" in line2 and "%" in line2):  
					csv_write_list.append( line2.split(' ')[8] )
					all_map = np.append(multi_map, np.float32( line2.split(' ')[8] ))
					count = count +1
				line2 = f2.readline()
			writ.writerow(csv_write_list)

			f0.close()

			epoch = int( weight_file.split(".")[0].split("_")[-1] )
			if(all_map[-1]>best_map):
				best_map = all_map[-1]
				best_map_iter = epoch
			if(len(all_map)>=2):
				if( (all_map[-1]-all_map[-2])/(all_map[-2]) > params_min_delta ):
					# baseline_map = multi_map[-1]
					epoch_count_baseline = 0
				else:
					epoch_count_baseline = epoch_count_baseline + 1
					if(epoch_count_baseline>= params_patience and epoch > params_min_epoch):
						stop_flag = 1
						break
			if(epoch > params_max_epoch):
				stop_flag = 1
				break
			
		f0 = open(csv_filename, 'a+')
		writ = csv.writer(f0, delimiter = ',')
		csv_write_list = []
		csv_write_list.append(first_run)
		csv_write_list.append(count_backup_files)
		csv_write_list.append( int(os.popen("ls "+params_backup_path+" -1 | wc -l").read()[:-1]) )
		writ.writerow(csv_write_list)
		f0.close()

	if(stop_flag):
		p.terminate()


	print("best map: " + str(best_map) )
	print("best map iter = "+ str(best_map_iter) )
	print("best map epoch = "+ str(best_map_iter*params_sub_batch/params_batch) )





