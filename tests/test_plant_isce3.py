import os
import pytest
import plant
import plant_isce3

NISAR_RSLC_FILE = 'data/envisat.h5'
DEM_FILE = 'data/constant_height.vrt'

GEOCODED_TIFF_FILE = 'output_data/gcov.tif'
NISAR_GCOV_RUNCONFIG = 'output_data/gcov.yaml'
NISAR_GCOV_FILE = 'output_data/gcov.h5'
RSLC_ORBIT_KML = 'output_data/rslc_orbit.kml'
GCOV_ORBIT_KML = 'output_data/gcov_orbit.kml'

TOPO_DIR = 'output_data/topo_dir'


def test_plant_isce3_info():
    plant_isce3.info(NISAR_RSLC_FILE)


def test_plant_isce3_util():

    if os.path.isfile(RSLC_ORBIT_KML):
        os.remove(RSLC_ORBIT_KML)

    plant_isce3.util(NISAR_RSLC_FILE, output_file=RSLC_ORBIT_KML,
                     orbit_kml=True, force=True)
    assert os.path.isfile(RSLC_ORBIT_KML)


def test_plant_isce3_topo():
    if os.path.isdir(TOPO_DIR):
        for f in os.listdir(TOPO_DIR):
            os.remove(os.path.join(TOPO_DIR, f))
        os.rmdir(TOPO_DIR)
    plant_isce3.topo(NISAR_RSLC_FILE, dem=DEM_FILE,
                     output_directory=TOPO_DIR)


def test_plant_isce3_geocode():
    if os.path.isfile(GEOCODED_TIFF_FILE):
        os.remove(GEOCODED_TIFF_FILE)
    plant_isce3.geocode(NISAR_RSLC_FILE, dem=DEM_FILE,
                        output_file=GEOCODED_TIFF_FILE, force=True)
    assert os.path.isfile(GEOCODED_TIFF_FILE)


def test_plant_isce3_gcov():

    if os.path.isfile(NISAR_GCOV_RUNCONFIG):
        os.remove(NISAR_GCOV_RUNCONFIG)
    if os.path.isfile(NISAR_GCOV_FILE):
        os.remove(NISAR_GCOV_FILE)
    if os.path.isfile(GCOV_ORBIT_KML):
        os.remove(GCOV_ORBIT_KML)

    plant_isce3.runconfig(
        NISAR_RSLC_FILE, dem=DEM_FILE,
        sas_output_file=NISAR_GCOV_FILE,
        output_file=NISAR_GCOV_RUNCONFIG,
        force=True)
    assert os.path.isfile(NISAR_GCOV_RUNCONFIG)

    plant.execute(f'gcov.py {NISAR_GCOV_RUNCONFIG} --no-log')
    assert os.path.isfile(NISAR_GCOV_FILE)

    plant_isce3.util(NISAR_GCOV_FILE, output_file=GCOV_ORBIT_KML,
                     orbit_kml=True, force=True)
    assert os.path.isfile(GCOV_ORBIT_KML)

    plant_isce3.info(NISAR_GCOV_FILE)
