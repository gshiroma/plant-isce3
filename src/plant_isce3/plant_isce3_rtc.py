#!/usr/bin/env python3

import os
import plant
import plant_isce3
from osgeo import gdal

import isce3


def get_parser():

    descr = ('')
    epilog = ''
    parser = plant.argparse(epilog=epilog,
                            description=descr,
                            input_file=1,
                            dem_file=2,
                            default_options=1,
                            multilook=1,
                            geo=1,
                            output_file=2)

    plant_isce3.add_arguments(parser,
                              abs_cal_factor=1,
                              frequency=1,
                              burst_ids=1,
                              epsg=1,
                              input_raster=1,
                              input_rtc=1,
                              native_doppler_grid=1,
                              orbit_files=1)

    parser.add_argument('--sim', '--simulate-backscatter', '--simamp',
                        '--sim-amp', '--simulate',
                        dest='simulate',
                        action='store_true',
                        help='Simulate backscatter '
                        '(no input backscatter image is needed).')

    parser.add_argument('--area',
                        '--area-only',
                        dest='area_only',
                        action='store_true',
                        help='Save area (instead of area ratio).')

    parser.add_argument('--input-radiometry',
                        dest='input_radiometry',
                        type=str,
                        help='Input data radiometry. Options:'
                        'beta or sigma-ellipsoid')

    parser.add_argument('--output-radiometry',
                        '--output-terrain-radiometry',
                        dest='output_terrain_radiometry',
                        type=str,
                        help='Output data radiometry. Options:'
                        'sigma-naught or gamma-naught')

    parser.add_argument('--clip-min',
                        type=float,
                        dest='clip_min',
                        help='Clip (limit) min output values')

    parser.add_argument('--clip-max',
                        type=float,
                        dest='clip_max',
                        help='Clip (limit) max output values')

    parser.add_argument('--terrain', '--terrain-type',
                        '--rtc',
                        dest='terrain_correction_type',
                        type=str,
                        help="type of radiometric terrain correction: "
                        "'gamma-naught-david-small', "
                        "'gamma-naught-area-projection' "
                        "(default: %(default)s)",
                        default='gamma-naught-area-projection')

    parser.add_argument('--upsampling',
                        dest='geogrid_upsampling',
                        default=2,
                        type=int,
                        help='DEM upsample factor.')

    parser.add_argument('--rtc-min-value-db',
                        dest='rtc_min_value_db',
                        default=-30,
                        type=float,
                        help='RTC min. value in dB. -1 for disabled.'
                        ' Default: -30 dB.')

    parser.add_argument('--out-rdr',
                        '--out-geo-rdr',
                        '--output-rdr',
                        '--output-geo-rdr',
                        dest='out_geo_rdr',
                        type=str,
                        help='Output geo rdr.')

    parser.add_argument('--memory-mode',
                        dest='memory_mode',
                        type=str,
                        choices=['auto',
                                 'single-block',
                                 'run-time-efficient'],
                        help='Memory mode')

    parser.add_argument('--out-grid',
                        '--out-geo-grid',
                        dest='out_geo_grid',
                        type=str,
                        help='Output geo grid.')

    parser.add_argument('--out-rtc',
                        '--output-rtc',
                        dest='output_rtc',
                        type=str,
                        help=('Name of the output RTC area normalization'
                              ' factor (ANF) file'))

    parser.add_argument('--out-sigma',
                        dest='out_sigma',
                        type=str,
                        help=('Name of the output RTC beta-to-sigma factor'
                              ' file'))

    return parser


class PlantIsce3Rtc(plant_isce3.PlantIsce3Script):

    def __init__(self, parser, argv=None):

        super().__init__(parser, argv)

    def run(self):

        if (not self.simulate and (self.out_geo_grid or self.out_geo_rdr)):
            self.print('ERROR options --out-geo-grid and out-geo-rdr require'
                       ' --simulate mode')
            return
        if self.output_rtc and self.simulate:
            self.print('ERROR options --output-rtc cannot be used along'
                       ' with the option --simulate')
            return
        for f in [self.output_file, self.out_geo_grid, self.out_geo_rdr,
                  self.out_sigma, self.output_rtc]:
            ret = self.overwrite_file_check(f)
            if not ret:
                self.print('Operation cancelled.', 1)
                return

        plant_product_obj = self.load_product()
        radar_grid_ml = plant_product_obj.get_radar_grid_ml()
        orbit = plant_product_obj.get_orbit()
        doppler = plant_product_obj.get_grid_doppler()

        output_dir = os.path.dirname(self.output_file)
        if output_dir and not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        dem = plant_isce3.get_isce3_raster(self.dem_file)
        if self.epsg is None:
            if dem.get_epsg() == 0 or dem.get_epsg() < -9000:
                print(f'WARNING invalid DEM EPSG: {dem.get_epsg()}')
                print('Updating DEM EPSG to 4326...')
                dem.set_epsg(4326)
            self.epsg = dem.get_epsg()

        rtc_kwargs = self.get_rtc_kwargs(
            radar_grid_ml, dem)

        isce3_temporary_format = plant_isce3.get_isce3_temporary_format(
            self.output_file)

        if self.simulate:
            print('*** rtc_kwargs: ', rtc_kwargs)

            output_raster_obj = plant_isce3.get_isce3_raster(
                self.output_file,
                radar_grid_ml.width,
                radar_grid_ml.length,
                1,
                gdal.GDT_Float32,
                isce3_temporary_format)

            if not self.out_geo_grid and not self.out_geo_rdr:
                print('*** calling pyRTC')

                isce3.geometry.compute_rtc(radar_grid_ml,
                                           orbit,
                                           doppler,
                                           dem,
                                           output_raster_obj,
                                           **rtc_kwargs)
            else:
                print('*** calling pyRTCBBox')

                print('*** self.plant_geogrid_obj.y0:',
                      self.plant_geogrid_obj.y0)
                print('*** self.plant_geogrid_obj.step_y:',
                      self.plant_geogrid_obj.step_y)
                print('*** self.plant_geogrid_obj.x0:',
                      self.plant_geogrid_obj.x0)
                print('*** self.plant_geogrid_obj.step_x:',
                      self.plant_geogrid_obj.step_x)
                print('*** self.plant_geogrid_obj.length:',
                      self.plant_geogrid_obj.length)
                print('*** self.plant_geogrid_obj.width:',
                      self.plant_geogrid_obj.width)
                isce3.geometry.compute_rtc_bbox(dem,
                                                output_raster_obj,
                                                radar_grid_ml,
                                                orbit,
                                                doppler,
                                                self.plant_geogrid_obj.y0,
                                                self.plant_geogrid_obj.step_y,
                                                self.plant_geogrid_obj.x0,
                                                self.plant_geogrid_obj.step_x,
                                                self.plant_geogrid_obj.length,
                                                self.plant_geogrid_obj.width,
                                                self.epsg,
                                                **rtc_kwargs)

        else:
            if self.clip_min is not None:
                rtc_kwargs['clip_min'] = self.clip_min

            if self.clip_max is not None:
                rtc_kwargs['clip_max'] = self.clip_max

            if self.abs_cal_factor is not None:
                rtc_kwargs['abs_cal_factor'] = self.abs_cal_factor

            if (plant_product_obj.sensor_name == 'Sentinel-1'):

                input_raster = plant_product_obj.get_sentinel_1_input_raster(
                    self.input_raster,
                    clip_min=0.000001)

            else:
                input_raster = self.get_input_raster_from_nisar_product(
                    plant_product_obj=plant_product_obj)

            if self.input_rtc:
                input_rtc_obj = plant_isce3.get_isce3_raster(self.input_rtc)
                rtc_kwargs['input_rtc'] = input_rtc_obj

            input_raster_obj = plant_isce3.get_isce3_raster(input_raster)
            input_dtype = input_raster_obj.datatype()

            if input_dtype == gdal.GDT_CFloat32:
                output_dtype = gdal.GDT_Float32
            elif input_dtype == gdal.GDT_CFloat64:
                output_dtype = gdal.GDT_Float64
            else:
                output_dtype = input_dtype

            nbands = input_raster_obj.num_bands

            print('number of bands:', nbands)
            output_raster_obj = plant_isce3.get_isce3_raster(
                self.output_file,
                radar_grid_ml.width,
                radar_grid_ml.length,
                nbands,
                output_dtype,
                isce3_temporary_format)

            print('*** rtc_kwargs: ', rtc_kwargs)

            isce3.geometry.apply_rtc(
                radar_grid_ml,
                orbit,
                doppler,
                input_raster_obj,
                dem,
                output_raster_obj,

                **rtc_kwargs)
            del input_raster_obj
        del output_raster_obj
        if self.out_geo_grid:
            out_geo_grid_obj = rtc_kwargs['out_geo_grid']
            del out_geo_grid_obj
            plant.append_output_file(self.out_geo_grid)
        if self.out_geo_rdr:
            out_geo_rdr_obj = rtc_kwargs['out_geo_rdr']
            del out_geo_rdr_obj
            plant.append_output_file(self.out_geo_rdr)
        del rtc_kwargs

        if self.input_rtc and not self.simulate:
            del input_rtc_obj

        ret_dict = {}
        ret_dict['output_file'] = self.output_file
        plant.append_output_file(self.output_file)

        if self.output_rtc:
            ret_dict['output_rtc'] = self.output_rtc
        if self.out_geo_grid:
            ret_dict['out_geo_grid'] = self.out_geo_grid
        if self.out_geo_rdr:
            ret_dict['out_geo_rdr'] = self.out_geo_rdr
        if self.out_sigma:
            ret_dict['out_sigma'] = self.out_sigma

        self.update_output_format(ret_dict)

        return self.output_file

    def get_rtc_kwargs(self, radar_grid_ml, dem):
        rtc_kwargs = {}
        flag_sigma = (self.input_radiometry is not None and
                      'sigma' in self.input_radiometry.lower())

        if flag_sigma:
            print('## input terrain radiometry convention: sigma-0'
                  ' (ellipsoid)')
            rtc_kwargs['input_terrain_radiometry'] = \
                isce3.geometry.RtcInputTerrainRadiometry.SIGMA_NAUGHT_ELLIPSOID
        else:
            print('## input terrain radiometry convention: beta-0')
            rtc_kwargs['input_terrain_radiometry'] = \
                isce3.geometry.RtcInputTerrainRadiometry.BETA_NAUGHT

        flag_output_terrain_radimetry_is_sigma = \
            (self.output_terrain_radiometry is not None and
             'sigma' in self.output_terrain_radiometry.lower())

        if flag_output_terrain_radimetry_is_sigma:
            print('## output terrain radiometry convention: sigma-0')
            rtc_kwargs['output_terrain_radiometry'] = \
                isce3.geometry.RtcOutputTerrainRadiometry.SIGMA_NAUGHT
        else:
            print('## output terrain radiometry convention: gamma-0')
            rtc_kwargs['output_terrain_radiometry'] = \
                isce3.geometry.RtcOutputTerrainRadiometry.GAMMA_NAUGHT

        if self.geogrid_upsampling is not None:
            rtc_kwargs['geogrid_upsampling'] = self.geogrid_upsampling

        if self.area_only:
            rtc_kwargs['rtc_area_mode'] = \
                isce3.geometry.RtcAreaMode.AREA
        else:
            rtc_kwargs['rtc_area_mode'] = \
                isce3.geometry.RtcAreaMode.AREA_FACTOR

        if self.memory_mode == 'single-block':
            rtc_kwargs['memory_mode'] = \
                isce3.geocode.GeocodeMemoryMode.SINGLE_BLOCK
        elif self.memory_mode == 'blocks-geogrid':
            rtc_kwargs['memory_mode'] = \
                isce3.geocode.GeocodeMemoryMode.BLOCKS_GEOGRID
        elif self.memory_mode == 'blocks-geogrid-and-radargrid':
            rtc_kwargs['memory_mode'] = \
                isce3.geocode.GeocodeMemoryMode.BLOCKS_GEOGRID_AND_RADARGRID

        flag_rtc_bilinear_distribution = (
            self.terrain_correction_type is not None and
            (('DAVID' in self.terrain_correction_type.upper() and
             'SMALL' in self.terrain_correction_type.upper()) or
             ('BILINEAR' in self.terrain_correction_type.upper() and
             'DISTR' in self.terrain_correction_type.upper())))

        print('*** flag_rtc_bilinear_distribution:',
              flag_rtc_bilinear_distribution)

        flag_rtc_area_proj = (
            (self.terrain_correction_type is not None and
             'AREA' in self.terrain_correction_type.upper() and
             'PROJ' in self.terrain_correction_type.upper()) or
            self.output_mode_area_gamma_naught or
            self.output_mode_interp_gamma_naught)

        print('*** flag_rtc_area_proj:', flag_rtc_area_proj)

        if flag_rtc_bilinear_distribution:
            print('## RTC algorithm: Bilinear Distribution')
            rtc_kwargs['rtc_algorithm'] = \
                isce3.geometry.RtcAlgorithm.RTC_BILINEAR_DISTRIBUTION
        else:
            print('## RTC algorithm: Area Projection')
            rtc_kwargs['rtc_algorithm'] = \
                isce3.geometry.RtcAlgorithm.RTC_AREA_PROJECTION

        if self.rtc_min_value_db is not None and self.rtc_min_value_db != -1:
            rtc_kwargs['rtc_min_value_db'] = self.rtc_min_value_db

        if self.out_sigma:
            print('*** geogrid width: ', dem.width)
            print('*** geogrid length: ', dem.length)
            out_sigma_obj = self._create_output_raster(
                self.out_sigma,
                width=radar_grid_ml.width,
                length=radar_grid_ml.length,
                nbands=1)
            rtc_kwargs['out_sigma'] = out_sigma_obj
            self.output_files.append(self.out_sigma)

        if self.output_rtc:
            print('*** geogrid width: ', dem.width)
            print('*** geogrid length: ', dem.length)
            output_rtc_obj = self._create_output_raster(
                self.output_rtc,
                width=radar_grid_ml.width,
                length=radar_grid_ml.length,
                nbands=1)
            rtc_kwargs['output_rtc'] = output_rtc_obj
            self.output_files.append(self.output_rtc)

        if not self.out_geo_grid and not self.out_geo_rdr:
            return rtc_kwargs

        self.update_geogrid(radar_grid_ml, dem)

        if self.out_geo_grid:
            out_geo_grid_obj = self._create_output_raster(
                self.out_geo_grid,
                width=self.plant_geogrid_obj.width * self.geogrid_upsampling,
                length=self.plant_geogrid_obj.length * self.geogrid_upsampling,
                nbands=2, gdal_dtype=gdal.GDT_Float64)
            rtc_kwargs['out_geo_grid'] = out_geo_grid_obj
            self.output_files.append(self.out_geo_grid)

        if self.out_geo_rdr:
            out_geo_rdr_obj = self._create_output_raster(
                self.out_geo_rdr,
                width=self.plant_geogrid_obj.width *
                self.geogrid_upsampling +
                1,
                length=self.plant_geogrid_obj.length *
                self.geogrid_upsampling +
                1,
                nbands=2,
                gdal_dtype=gdal.GDT_Float64)
            rtc_kwargs['out_geo_rdr'] = out_geo_rdr_obj
            self.output_files.append(self.out_geo_rdr)

        return rtc_kwargs


def main(argv=None):
    with plant.PlantLogger():
        parser = get_parser()
        with PlantIsce3Rtc(parser, argv) as self_obj:
            ret = self_obj.run()
        return ret


def main_cli(*args, **kwargs):
    main(*args, **kwargs)


if __name__ == '__main__':
    main()
