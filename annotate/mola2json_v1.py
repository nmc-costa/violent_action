#!/usr/bin/env python
# coding: utf-8

# # Create INCAR and INVICON MOLA JSON
# version: 1
# 
# info:
# - Create standard MOLA JSON
# 
# author: nuno costa


"""
# ## MOLA Annotations Data Format

# If you wish to combine multiple datasets, it is often useful to convert them into a unified data format. 
# 
# Objective: 

# In[2]:

 #ANNOTATIONS FORMAT (BASED ON COCO)

 #Annotations format keys:

 { "info": None, 
   "licenses": [], TODO
   "categories": [], 
   "images": [],
   "annotations": [],
   "videos": [], TODO
   "tracks": [], TODO
   "segment_info": [], TODO
   "datasets": [{'name': 'INCAR', 'id': 1}, {'name': 'INVICON', 'id': 2}] 
 }

 #1 object definition:

 info{
     "year": int, 
     "version": str, 
     "description": str, 
     "contributor": str, 
     "url": str, 
     "date_created": datetime,
 }
 
 license{
     "id": int, 
     "name": str, 
     "url": str,
 }
 
 category{
     "id": int, 
     "name": str, 
     "supercategory": str,
 }
 
 image: {
     "id" : int,
     "video_id": int, #TODO
     "file_name" : str,
     "license" : int,
     # Redundant fields for COCO-compatibility
     "width": int,
     "height": int,
     "frame_index": int,
     "date_captured": datetime,
 
 annotation: {
     "category_id": int
     "image_id": int,
     "track_id": int,
     "bbox": [x,y,width,height],
     "area": float,
     # Redundant field for compatibility with COCO scripts
     "id": int,
     "iscrowd": 0 or 1,  (iscrowd=1) are used to label large groups of objects (e.g. a crowd of people)
     "segmentation": RLE(iscrowd=1) or [polygon](iscrowd=0), 
     
 }
 
 video: { #TODO
     "id": int,
     "name": str,
     "width" : int,
     "height" : int,
     "metadata": dict,  # Metadata about the video
 }
 
 segment{ #TODO
     "id": int, 
     "category_id": int, 
     "area": int, 
     "bbox": [x,y,width,height], 
     # Redundant field for compatibility with COCO scripts
     "iscrowd": 0 or 1,
 }
 
    
 track: { #TODO
     "id": int,
     "category_id": int,
     "video_id": int
 }

"""
# ## SETUP

import platform 
import json
import os
from tqdm import tqdm
import argparse
import datetime


# ## Functions
def init_json(file='mola.json'):
    output = {
        "info": None,
        "licenses": [],
        "categories": [],
        "videos": [],
        "images": [],
        "tracks": [],
        "segment_info": [],
        "annotations": [],
        "datasets": [] #[{'name': 'COCO', 'id': 1}, {'name': 'TAO', 'id': 2}]
    }
    output['info'] = {
        "description": "MOLA Dataset",
        "url": "",
        "version": "1",
        "year": 2021,
        "date_created": datetime.datetime.utcnow().isoformat(' ')
    }

    with open(file, 'w') as f:
        json.dump(output, f)
    print("JSON INITIATED : {}".format(file))

def parse_path(path):
    parsed_path = path.replace('\\', '/')
    parsed_path = parsed_path.replace('\ ', '/')
    return parsed_path

def fix_pahts(gt):
    #fix gt datasource
    paths=gt['gTruth']['DataSource']
    if isinstance(paths, dict) and 'Source' in paths: paths=paths['Source']
    originalpath=paths[0]
    for p in paths:
        if p.find("gt") >-1 : 
            originalpath=p
            break
    originalpath=parse_path(originalpath)
    paths=[parse_path(p) for p in paths]
    paths = ['/'.join(originalpath.split('/')[:-1]+[p.split('/')[-1]]) if p.find("MATLAB") > -1 else p for p in paths]  #remove MATLAB BUG: 'C:\\Tools\\MATLAB\\R2020a\\examples\\symbolic\\data\\196.png'
    paths = ['/'.join(p.split('/')[-7:]) for p in paths] #remove root dir 
    gt['gTruth']['DataSource']=paths
    return gt

def import_categories(molajson, gt, start_id=0):
    # IMPORT categories name and id
    cat_l=[]
    cat_l_id=[]
    cat_l_dset=[]
    cat=gt['gTruth']['LabelDefinitions']
    for i,c in enumerate(tqdm(cat)):
        cat_l.append(c['Name'])
        cat_l_id.append(start_id+i+1) # id start from 1
        cat_l_dset.append(1) # dataset index
        molajson['categories'].append({'name':cat_l[i],'id':cat_l_id[i],'dataset':cat_l_dset[i]})
    # ADDITIONAL CATEGORIES: MANUAL
    name='NONVIOLENT'
    cid=len(cat_l)+1
    dset=1
    molajson['categories'].append({'name':name,'id':cid,'dataset':dset})
    cat_l.append(name)
    cat_l_id.append(cid)
    cat_l_dset.append(dset)
    print("\n>> categories:\n", molajson['categories'][-2:])
    return molajson, cat_l, cat_l_id, cat_l_dset

def import_images(molajson, gt, start_id=0):
    # images filepath and id
    img_l=[]
    img_l_id=[]
    img=gt['gTruth']['DataSource']
    for i,im in enumerate(tqdm(img)):
        img_l.append(im)
        img_l_id.append(start_id+i+1) # id start from 1
        molajson['images'].append({'file_name':img_l[i],
                                   'id':img_l_id[i],
                                   'caption':img_l[i].split('/')[-4], # scenario
                                   'dataset':1})
    print("\n>> images:\n", molajson['images'][-2:])
    return molajson, img_l, img_l_id

def create_annotations(molajson, gt, res, cat_l, cat_l_id, cat_l_dset, img_l_id, start_id=0):
    # annotations category_id, image_id, bbox, and dataset
    ann_id=[]
    ann_catid=[]
    ann_imgid=[]
    ann_bbox=[]
    ann_dset=[]
    labels=gt['gTruth']['LabelData']
    for i,l in enumerate(tqdm(labels)):
        annid=start_id+i+1
        catidx=cat_l.index("VIOLENT")
        if not l["VIOLENT"]: catidx=cat_l.index("NONVIOLENT")
        catid=cat_l_id[catidx]
        dataset=cat_l_dset[catidx]
        imgidx=i
        imgid=img_l_id[imgidx]
        bbox=[0, 0, res['rgb'][0], res['rgb'][1]] # [x,y,width,height], #default RGB
        area=res['rgb'][0]*res['rgb'][1] #default RGB
        ann_id.append(annid)
        ann_catid.append(catid)
        ann_imgid.append(imgid)
        ann_bbox.append(bbox)
        ann_dset.append(dataset)
        molajson['annotations'].append({'id':annid,
                                        'category_id':catid,
                                        'image_id':imgid,
                                        'bbox': bbox,
                                        'area': area,
                                        'iscrowd': 0,
                                        'dataset':dataset})
    print("\n>> annotations:\n", molajson['annotations'][-2:])
    return molajson, ann_id, ann_catid, ann_imgid, ann_bbox, ann_dset
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=str, default='D:/external_datasets/MOLA/', help='root dir of datasets')
    parser.add_argument('--datasets', nargs='+', default=['INCAR'], help='list of datasets')
    args = parser.parse_args()
    root=args.root
    datasets=args.datasets

    #Define root dir dependent on OS
    rdir=root #WARNING needs to be root datasets
    print('OS: {}'.format(platform.platform()))
    print('root dir: {}'.format(rdir))

    # define resolutions
    res={
        'rgb': [2048, 1536], #w,h
        'thermal': [640,512],
        'pointcloud': [640,576]
    }

    # FOR LOOP"
    datasetsdir = os.listdir(rdir)
    missing_gt_json=[]
    missing_gt_mat=[]
    label_folder="gt"
    label_fname="gt.json"
    label_mat_fname="gt.m"
    for dataset in datasetsdir:
        if dataset in datasets:
            daysdir = os.path.join(rdir, dataset)
            if not os.path.isdir(daysdir): continue  # test if is a folder
            print(">>>\n EXTRACTING DATASET: "+dataset)
            #INIT JSON
            molafile=rdir+dataset+'/'+'mola.json'
            init_json(file=molafile)
            molajson =  json.load(open(molafile))
            molajson['datasets'] = [{'name': d, 'id': i+1} for i,d in enumerate(datasets)]
            with open(molafile, 'w') as f:
                json.dump(molajson, f)
            days = os.listdir(daysdir)
            imported_cats = False
            cat_start_id = 0
            img_start_id = 0
            ann_start_id = 0
            cat_l, cat_l_id, cat_l_dset = [], [], []
            img_l, img_l_id = [], []
            ann_id, ann_catid, ann_imgid, ann_bbox, ann_dset = [], [], [], [], []
            for day in days:
                sessiondir = os.path.join(daysdir, day)
                if not os.path.isdir(sessiondir): continue  # test if is a folder
                sessions = os.listdir(sessiondir)
                for session in sessions:
                    scenariosdir = os.path.join(sessiondir, session)
                    if not os.path.isdir(scenariosdir): continue  # test if is a folder
                    scenarios = os.listdir(scenariosdir)
                    for scenario in scenarios:
                        imgdir = os.path.join(scenariosdir, scenario)
                        if not os.path.isdir(imgdir): continue  # test if is a folder
                        labeldir = os.path.join(imgdir, label_folder)
                        # if not os.path.isdir(labeldir): continue #should exist
                        filename = os.path.join(labeldir, label_fname)
                        try:
                            gt = json.load(open(filename))
                        except:
                            print(">>>>>>>MISSING: ", filename)
                            missing_files.append(filename)
                            missing_gt_json.append(filename)
                            if not os.path.isfile(filename.replace(label_fname, label_mat_fname)): missing_gt_mat.append(filename.replace(label_fname, label_mat_fname))
                            continue
                        # fix gt paths
                        gt = fix_pahts(gt)
                        # update molajson
                        if not imported_cats:  # only imports one time
                            molajson, cat_l, cat_l_id, cat_l_dset = import_categories(molajson, gt, start_id=cat_start_id)
                            imported_cats = True
                        molajson, img_l, img_l_id = import_images(molajson, gt, start_id=img_start_id)
                        molajson, ann_id, ann_catid, ann_imgid, ann_bbox, ann_dset = create_annotations(molajson, gt, res,
                                                                                                        cat_l, cat_l_id,
                                                                                                        cat_l_dset, img_l_id,
                                                                                                        start_id=ann_start_id)
                        # update start ids to the last id
                        cat_start_id = cat_l_id[-1]
                        img_start_id = img_l_id[-1]
                        ann_start_id = ann_id[-1]

            # results
            for k in molajson:
                print(k, len(molajson[k]))

            # # Save
            print('\n >> SAVING...')
            jsonfile=molafile
            with open(jsonfile, 'w') as f:
                json.dump(molajson, f)
            with open(jsonfile.replace('.json', '_missing_gtmat.txt'),'w') as f:
                f.write(str(missing_gt_mat))
            with open(jsonfile.replace('.json', '_missing_gtjson.txt'),'w') as f:
                f.write(str(missing_gt_mat))
            print("JSON SAVED : {} \n".format(jsonfile))

            #retest results
            molajson =  json.load(open(molafile))
            for k in molajson:
                print(k, len(molajson[k]))







