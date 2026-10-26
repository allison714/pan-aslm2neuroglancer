@echo off
REM Stitch the 560 channel locally, reusing the registration from the finished 488 run.
REM Runs inside the dataset folder so outputs land next to the 488 outputs.
setlocal
set DATASET=F:\Sept 2026\pan-ASLM\Allison_bestchances_images_multichannel_multitiling
set PI2=C:\Users\admin\OneDrive\Desktop\pan-aslm2neuroglancer\pi2-v4.5-win-no-opencl
set SRC_SAMPLE=Allison_bestchances_images_multichan
set SETTINGS=%~dp0stitch_settings_560.txt

call conda activate stitch_app || (echo [ERROR] conda env stitch_app not found & exit /b 1)
cd /d "%DATASET%" || (echo [ERROR] dataset folder not found & exit /b 1)
if not exist "RAW\Zstack00000560.tif" (echo [ERROR] RAW\Zstack00000560.tif missing & exit /b 1)

echo === %DATE% %TIME%  preparing 560 from 488 registration
python "%~dp0reuse_registration.py" --src-sample %SRC_SAMPLE% --dst-settings "%SETTINGS%" || exit /b 1

echo === %DATE% %TIME%  running nr_stitcher (560)
python "%PI2%\nr_stitcher.py" "%SETTINGS%" || (echo [ERROR] nr_stitcher failed & exit /b 1)

echo === %DATE% %TIME%  done. Output: %SRC_SAMPLE%_560_0.0_0.0_0.0_*x*x*.raw
pause
