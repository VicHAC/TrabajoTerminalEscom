import os
import numpy as np
import pandas as pd
from skimage import io
from skan import Skeleton, summarize
from scipy.sparse.csgraph import connected_components, shortest_path

def extract_microglia_metrics(skeleton_image_path: str) -> dict:
    """
    Extracts morphological metrics from a pre-skeletonized binary image.
    """
    image = io.imread(skeleton_image_path)
    
    if image.ndim > 2:
        image = image[:, :, 0]
    
    image = image > 0
    
    try:
        skeleton = Skeleton(image)
        summary = summarize(skeleton, separator='_')
    except Exception:
        skeleton = None
        summary = pd.DataFrame()
    
    if skeleton is not None:
        degrees = skeleton.degrees
        
        end_points = int(np.sum(degrees == 1))
        slab_voxels = int(np.sum(degrees == 2))
        junction_voxels = int(np.sum(degrees > 2))
        triple_points = int(np.sum(degrees == 3))
        quadruple_points = int(np.sum(degrees == 4))
        
        lines = len(summary)
        
        junction_indices = np.where(degrees > 2)[0]
        if len(junction_indices) > 0:
            junction_subgraph = skeleton.graph[junction_indices, :][:, junction_indices]
            junction_points, _ = connected_components(junction_subgraph, directed=False)
        else:
            junction_points = 0
            
        dist_col = 'branch_distance' if 'branch_distance' in summary.columns else 'branch-distance'
        
        if lines > 0 and dist_col in summary.columns:
            avg_branch_length = float(summary[dist_col].mean())
            max_branch_length = float(summary[dist_col].max())
        else:
            avg_branch_length = 0.0
            max_branch_length = 0.0
            
        if skeleton.graph.nnz > 0:
            dist_matrix = shortest_path(csgraph=skeleton.graph, directed=False)
            dist_matrix[np.isinf(dist_matrix)] = 0
            longest_shortest_path = float(dist_matrix.max())
        else:
            longest_shortest_path = 0.0
    else:
        end_points = slab_voxels = junction_voxels = triple_points = quadruple_points = 0
        lines = junction_points = 0
        avg_branch_length = max_branch_length = longest_shortest_path = 0.0
    
    filename = os.path.basename(skeleton_image_path)
    
    metrics = {
        "image": filename,
        "lines": int(lines),
        "junction points": int(junction_points),
        "end points": int(end_points),
        "junction voxels": int(junction_voxels),
        "slab voxels": int(slab_voxels),
        "average branch length": round(avg_branch_length, 2),
        "triple points": int(triple_points),
        "quadruple points": int(quadruple_points),
        "maximum branch length": round(max_branch_length, 2),
        "longest shortest path": round(longest_shortest_path, 2)
    }
    
    return metrics

def process_directory(directory_path: str, output_excel: str):
    """
    Iterates over skeletonized images in a directory, extracts metrics, 
    and exports the consolidated data to an Excel file.
    """
    metrics_list = []
    
    for filename in os.listdir(directory_path):
        if filename.lower().endswith(('.png', '.tif', '.tiff', '.jpg', '.jpeg')):
            file_path = os.path.join(directory_path, filename)
            try:
                metrics = extract_microglia_metrics(file_path)
                metrics_list.append(metrics)
            except Exception as e:
                print(f"Failed to process {filename}: {e}")
                
    if metrics_list:
        df = pd.DataFrame(metrics_list)
        df.to_excel(output_excel, index=False)
    else:
        print("No metrics extracted.")

if __name__ == "__main__":
    # Example test call (uncomment and modify to run as standalone script)
    # process_directory("input_skeleton_directory", "output_metrics.xlsx")
    pass
