# Running NRStitcher on the Yale Misha (Slurm) Cluster

This guide explains how to use the Streamlit configurator app to generate a stitching job and queue it up on the Yale Center for Research Computing (YCRC) Misha cluster.

## 1. Prepare your Run Bundle (Local PC)

The Streamlit app does not run the heavy image stitching itself. Instead, it creates a "Run Bundle"—a folder packed with the configuration text files and a Slurm batch script (`.sbatch`) that the Misha cluster needs to execute the job.

1.  **Open the Configurator**: Launch the `app.py` Streamlit interface on your local computer.
2.  **Target Environment**: Select **"Misha Cluster (Slurm)"** from the dropdown at the top.
3.  **Data Path (Crucial Step)**: In the **Raw Data Directory** field, you *must* provide the folder path exactly as Misha sees it on the network. 
    *   *Correct*: `/project/pi_name/username/dataset` or `/scratch/username/dataset`
    *   *Incorrect*: `Z:\projects\...` or `C:\Users\...`
4.  **Dataset Name**: This becomes the name of your output folder and your Slurm job. The recommended format is `YYMMDD_ROI_TilesX_TilesY_ZSlices` (e.g., `260302_Hippocampus_4x4x7200`).
5.  **Cluster Settings**: 
    *   Enable **"Auto-Recommend Resources"** to let the app pick the correct CPU, Memory, and Slurm Partition (`devel`, `day`, or `week`) based on YCRC rules.
    *   *Optional but Recommended*: Check the box for **"Stage heavy I/O to local /tmp"**. This copies your images to the computing node's local hard drive before stitching, greatly speeding up processing.
6.  **Generate**: Click "Generate Run Bundle" at the bottom. A new folder will be created locally (e.g., `260302_slurm_nr_260302_Hippocampus_4x4x7200`).

## 2. Transfer the Bundle to Misha

You must move this generated folder from your local computer to the cluster.

1.  **For Small Datasets (< 10GB)**: You can drag and drop the folder directly into the YCRC Open OnDemand file explorer, or use `scp`/SFTP (e.g., Cyberduck).
2.  **For Large Datasets (> 10GB)**: Always use **Globus**. It handles massive transfers reliably and quickly. Transfer the folder to your `/project` or `/scratch` space.

## 3. Submit the Job (Misha Cluster)

Now you tell Misha's "Slurm" scheduler to run the files inside your bundle.

1.  **Log In**: Go to the YCRC Open OnDemand portal (or SSH from your terminal: `ssh netid@misha.ycrc.yale.edu`).
2.  **Open a Terminal**: In Open OnDemand, click "Clusters" -> "Misha Shell Access".
3.  **Navigate to the Bundle**: Use the `cd` command to enter the folder you just uploaded.
    ```bash
    cd /path/to/your/uploaded_bundle_folder
    ```
4.  **Run the Job**: Tell the scheduler to queue your script.
    ```bash
    sbatch run_nrstitcher.sbatch
    ```
    *The terminal will reply with something like: `Submitted batch job 1234567`*

## 4. Monitor & Retrieve Your Results

You **do not** need to keep your terminal open or stay logged in while the job is running. Slurm handles it in the background!

### Checking on your Job
While the job is running (or queued), you can use these commands in the terminal:
*   **See where you are in the queue:** `squeue -u <your_netid>`
*   **Watch live CPU/RAM usage:** `jobstats 1234567` *(replace with your actual job ID)*

### Looking at Errors or Progress
Slurm creates two live text files in your bundle folder while it runs. You can open these to see what the script is currently printing:
*   `dataset_name_stitch_1234567.out` (Standard Print Outputs)
*   `dataset_name_stitch_1234567.err` (Errors and Warnings)

### When It Finishes
1.  Check exactly how much memory and time your job used: `seff 1234567` (This helps you optimize resources for next time!)
2.  Your stitched outputs (e.g., `.zarr` files, raw files, Neuroglancer info) will appear directly inside the bundle folder or the network data path you specified. If you checked the `/tmp` option in step 1, they are automatically copied back to your network folder at the very end of the script.
