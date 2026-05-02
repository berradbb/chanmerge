import os
import sys
import glob
import subprocess
from astropy.coordinates import SkyCoord
import astropy.units as u
from astroquery.heasarc import Heasarc

def auto_merge_obs(ra=None, dec=None, radius_arcmin=None, energy_band="broad", outdir=None):
    """
    ====================================================================
    Automated Chandra X-ray Data Pipeline
    ====================================================================
    Description:
        Queries HEASARC for Chandra observations within a specified radius 
        of a target RA/Dec, downloads the primary data, reprocesses it 
        with the latest calibrations, and merges it into a flux image.

    Required Parameters:
        ra (str)            : Right Ascension
        dec (str)           : Declination
        radius_arcmin (float): Search radius (arcminutes)

    Optional Parameters:
        energy_band (str)   : Energy band(s) to be extracted and merged. Default: "broad".
                              Available options and usage:
                              - Single band: "broad", "soft", "medium", or "hard".
                              - Multiple bands: Comma-separated without spaces (e.g., "soft,hard").
                              - All standard bands: Use "csc" to automatically generate
                                separate images for broad, soft, medium, and hard bands.
        outdir (str)        : Directory to save all downloaded and processed files. Default: obs_{ra}_{dec}.
        

    Usage Example:
        from chanmerge import auto_merge_obs
        
        auto_merge_obs(
            ra="13:25:27.6", 
            dec="-43:01:09", 
            radius_arcmin=15.0
        )
    ====================================================================
    """
    
    # ==========================================
    # INPUT VALIDATION & AUTOMATIC HELP TRIGGER
    # ==========================================
    # 1. Check for missing required inputs
    if ra is None or dec is None or radius_arcmin is None:
        print("\n[!] ERROR: Missing required parameters.")
        print("Please review the function documentation below:\n")
        print(auto_merge_obs.__doc__)
        return

    # 2. Type validation for radius
    try:
        radius_arcmin = float(radius_arcmin)
    except (ValueError, TypeError):
        print("\n[!] ERROR: 'radius_arcmin' must be a numeric value (e.g., 15 or 15.0).")
        print("Please review the function documentation below:\n")
        print(auto_merge_obs.__doc__)
        return

    # ==========================================
    # PIPELINE EXECUTION
    # ==========================================
    print(f"\n--- Starting Chandra Pipeline for [{ra}, {dec}] ---")

    safe_ra = str(ra).replace(":", "")
    safe_dec = str(dec).replace(":", "")
    auto_dirname = f"obs_{safe_ra}_{safe_dec}"

    if outdir is None:
        outdir = auto_dirname
    else:
        original_input = outdir 
        outdir = str(outdir).replace(":", "-").replace("/", "_").replace("\\", "_")
        outdir = outdir.lstrip('.')
        
        if not outdir:
            outdir = auto_dirname
            print(f"\n [!] WARNING: Your requested directory name '{original_input}' was invalid or entirely stripped for safety.")
            print(f"     Falling back to auto-generated name: '{outdir}'\n")
    
    print("\n[1/4] Querying HEASARC database...")
    heasarc = Heasarc()
    try:
        target_coordinate = SkyCoord(ra, dec, unit=(u.hourangle, u.deg), frame='icrs')
    except Exception as e:
        print(f"\n[!] ERROR: Invalid coordinate format. Details: {e}")
        return

    table = heasarc.query_region(target_coordinate, catalog='chanmaster', radius=radius_arcmin * u.arcmin)
    
    obsid_list = table['obsid'].tolist()
    clean_obsid_list = [str(obs).strip() for obs in obsid_list]
    num_obs = len(clean_obsid_list)
    
    print(f"Search complete. Found {num_obs} observations in a {radius_arcmin} arcmin radius.")
    
    
    # ==========================================
    # SANITY CHECK & STORAGE ESTIMATOR
    # ==========================================
    if num_obs == 0:
        print("No observations found in this region. Exiting pipeline.")
        return 
        
    try:
        # Extract exposure times from the HEASARC table
        total_exposure_sec = sum(table['exposure'])
        
        # Raw Data: ~50 MB fixed overhead per observation + ~2 MB per kilosecond (1000s) of exposure
        estimated_raw_mb = (num_obs * 50.0) + ((total_exposure_sec / 1000.0) * 2.0)
        
        # Processed Footprint: Repro (level 2 events, bad pixel maps) + Merged files (exposure maps)
        # typically take about 3.5x to 4x the space of the raw data.
        estimated_total_mb = estimated_raw_mb * 3.5

        def format_size(size_in_mb):
            return f"{size_in_mb / 1024:.2f} GB" if size_in_mb >= 1000 else f"{size_in_mb:.0f} MB"
            
        print("\n--- [STORAGE FOOTPRINT ESTIMATE] ---")
        print(f" Total Exposure Time : {total_exposure_sec / 1000:.1f} kiloseconds")
        print(f" Estimated Download  : ~{format_size(estimated_raw_mb)}")
        print(f" Final Disk Footprint: ~{format_size(estimated_total_mb)} (after reprocessing & merging)")
        print("------------------------------------\n")
        
    except KeyError:
        # Fallback in case the 'exposure' column is missing from the HEASARC response
        print("\n--- [STORAGE FOOTPRINT ESTIMATE] ---")
        print(f" Estimated Download  : ~{num_obs * 100} MB")
        print(f" Final Disk Footprint: ~{num_obs * 350} MB")
        print("\n [!] WARNING: These are rough estimates based on average observation sizes.")
        print(" [!] It is HIGHLY RECOMMENDED to have at least TWICE the estimated disk space")
        print("     available to account for temporary files and processing overhead.")
        print("------------------------------------\n")

    user_input = input(f"> Do you want to proceed with {num_obs} observations? (y/n): ")
    if user_input.lower() != 'y':
        print("Pipeline aborted by the user. No files were downloaded.")
        return 

    print(f"\n[0/4] Preparing output directory: '{outdir}'...")
    os.makedirs(outdir, exist_ok=True)
        
    print("\n[2/4] Downloading primary data...")
    for obsid in clean_obsid_list:
        print(f"  -> Downloading ObsID: {obsid}")
        download_command = f"download_chandra_obsid {obsid}"
        subprocess.run(download_command, shell=True, check=True, cwd=outdir)
        
    print("\n[3/4] Reprocessing data with latest calibrations...")
    for obsid in clean_obsid_list:
        print(f"  -> Reprocessing ObsID: {obsid}")
        input_dir = str(obsid)
        output_dir = f"{obsid}/repro"
        
        repro_command = f"chandra_repro indir={input_dir} outdir={output_dir}"
        subprocess.run(repro_command, shell=True, check=True, cwd=outdir)
        subprocess.run("punlearn ardlib", shell=True, check=True, cwd=outdir)
        
    print("\n[4/4] Merging event files into a single flux image...")
    event_files_list = glob.glob(os.path.join(outdir, "*", "repro", "*_evt2.fits"))
    if not event_files_list:
        print("\n[!] ERROR: No reprocessed event files found. Merging failed.")
        return
        
    files_to_merge = ",".join(event_files_list)
    merged_dir = os.path.join(outdir, "merged_final_image")
    os.makedirs(merged_dir, exist_ok=True)
    outroot = os.path.join(merged_dir, "merged_obs")
    
    merge_command = f"merge_obs {files_to_merge} {outroot} bands={energy_band}"
    subprocess.run(merge_command, shell=True, check=True)
    
    print(f"\n--- Pipeline Completed Successfully! ---")
    print(f"All raw data, repro folders, and final merged products are inside '{outdir}'.")