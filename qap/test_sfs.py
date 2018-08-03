import unittest
import json
import numpy as np

test_sub_dir = "test_data"


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.float32):
            return float(obj)
        if isinstance(obj, np.int64):
            return int(obj)

        return json.JSONEncoder.default(self, obj)


def get_test_dir(key):

    import datetime
    import os

    time_stamp_string = datetime.datetime.strftime(datetime.datetime.now(), "%Y%m%d%H%M%S")
    working_dir = os.path.join('/tmp', '{0}_{1}'.format(key, time_stamp_string))
    os.makedirs(working_dir)

    return working_dir


class TestSFS(unittest.TestCase):

    def setUp(self):
        import os
        import pkg_resources as p

        self.func_reorient = \
            p.resource_filename("qap", os.path.join(test_sub_dir,
                                                    "func_reorient.nii.gz"))

        self.func_motion_corrected = \
            p.resource_filename("qap", os.path.join(test_sub_dir,
                                                    "func_motion_correct.nii.gz"))

        self.func_mask = \
            p.resource_filename("qap",
                                os.path.join(test_sub_dir,
                                             "fsl_bet_mask.nii.gz"))

        self.func_motion_estimates = \
            p.resource_filename("qap",
                                os.path.join(test_sub_dir,
                                             "func_motion_estimate.1D"))

    def test_calc_sfs(self):
        import json
        import os

        from qap.sfs import calc_sfs
        working_directory = get_test_dir('sfs')

        sfs = calc_sfs(self.func_reorient, self.func_mask, detrend_polynomial_order=2,
                       motion_regressors_filename=self.func_motion_estimates, friston_twentyfour=True, debug=True,
                       working_directory=working_directory)
        json_out_filename = os.path.join(working_directory, 'test_out.json')

        with open(json_out_filename, 'w') as ofd:
            json.dump(sfs, ofd, indent=2, cls=NumpyEncoder)

        assert sfs

    def test_calc_sfs_erode3(self):
        import json
        from qap.sfs import calc_sfs
        import os

        working_directory = get_test_dir('sfs_erode3')

        sfs = calc_sfs(self.func_reorient, self.func_mask, detrend_polynomial_order=2, mask_erosions=3, debug=True,
                       working_directory=working_directory)

        json_out_filename = os.path.join(working_directory, 'sfs_test_out.json')
        with open(json_out_filename, 'w') as ofd:
            json.dump(sfs, ofd, indent=2, cls=NumpyEncoder)

        assert sfs

    def test_calc_sfs_95pct_erode(self):
        import json
        from qap.sfs import calc_sfs
        import os

        working_directory = get_test_dir('sfs_95pct_erode')

        sfs = calc_sfs(self.func_reorient, self.func_mask, detrend_polynomial_order=2,
                       noise_voxel_standard_deviation_percentile=95, mask_erosions=3, debug=True,
                       working_directory=working_directory)

        json_out_filename = os.path.join(working_directory, 'sfs_test_out.json')
        with open(json_out_filename, 'w') as ofd:
            json.dump(sfs, ofd, indent=2, cls=NumpyEncoder)

        assert sfs

    def test_calc_sfs_motion_corrected(self):
        import json
        import os

        from qap.sfs import calc_sfs
        working_directory = get_test_dir('sfs_moco')

        sfs = calc_sfs(self.func_motion_corrected, self.func_mask, detrend_polynomial_order=2, mask_erosions=3,
                       motion_regressors_filename=self.func_motion_estimates, friston_twentyfour=True, debug=True,
                       working_directory=working_directory)
        json_out_filename = os.path.join(working_directory, 'test_out.json')

        with open(json_out_filename, 'w') as ofd:
            json.dump(sfs, ofd, indent=2, cls=NumpyEncoder)

        assert sfs
