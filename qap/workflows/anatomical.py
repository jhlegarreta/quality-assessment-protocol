def anatomical_reorient_workflow(workflow, resource_pool, config, name="_"):
    """Build a Nipype workflow to deoblique and reorient an anatomical scan
    from a NIFTI file.

    - This is a seminal workflow that can only take an input directly from
      disk (i.e. no Nipype workflow connections/pointers, and this is where
      the pipeline will actually begin). For the sake of building the
      pipeine in reverse, if this workflow is called when there is no input
      file available, this function will return the unmodified workflow and
      resource pool directly back.
    - In conjunction with the other workflow-building functions, if this
      function returns the workflow and resource pool unmodified, each
      function up will do the same until it reaches the top level, allowing
      the pipeline builder to continue "searching" for a base-level input
      without crashing at this one.

    Expected Resources in Resource Pool
      - anatomical_scan: The raw anatomical scan in a NIFTI image.

    New Resources Added to Resource Pool
      - anatomical_reorient: The deobliqued, reoriented anatomical scan.

    Workflow Steps
      1. AFNI's 3drefit to deoblique the anatomical scan.
      2. AFNI's 3dresample to reorient the deobliqued anatomical scan to RPI.

    :type workflow: Nipype workflow object
    :param workflow: A Nipype workflow object which can already contain other
                     connected nodes; this function will insert the following
                     workflow into this one provided.
    :type resource_pool: dict
    :param resource_pool: A dictionary defining input files and pointers to
                          Nipype node outputs / workflow connections; the keys
                          are the resource names.
    :type config: dict
    :param config: A dictionary defining the configuration settings for the
                   workflow, such as directory paths or toggled options.
    :type name: str
    :param name: (default: "_") A string to append to the end of each node
                 name.
    :rtype: Nipype workflow object
    :return: The Nipype workflow originally provided, but with this function's
              sub-workflow connected into it.
    :rtype: dict
    :return: The resource pool originally provided, but updated (if
             applicable) with the newest outputs and connections.
    """

    import nipype.pipeline.engine as pe
    from nipype.interfaces.afni import preprocess

    if "anatomical_scan" not in resource_pool.keys():
        return workflow, resource_pool

    elif "s3://" in resource_pool["anatomical_scan"]:
        from qap.cloud_utils import download_single_s3_path
        resource_pool["anatomical_scan"] = \
            download_single_s3_path(resource_pool["anatomical_scan"], config)

    try:
        anat_deoblique = pe.Node(interface=preprocess.Refit(),
                                 name='anat_deoblique%s' % name)
    except AttributeError:
        from nipype.interfaces.afni import utils as afni_utils
        anat_deoblique = pe.Node(interface=afni_utils.Refit(),
                                 name='anat_deoblique%s' % name)

    anat_deoblique.inputs.in_file = resource_pool["anatomical_scan"]
    anat_deoblique.inputs.deoblique = True

    workflow.add_nodes([anat_deoblique])

    try:
        anat_reorient = pe.Node(interface=preprocess.Resample(),
                                name='anat_reorient%s' % name)
    except AttributeError:
        if not afni_utils:
            from nipype.interfaces.afni import utils as afni_utils
        anat_reorient = pe.Node(interface=afni_utils.Resample(),
                                 name='anat_reorient%s' % name)

    anat_reorient.inputs.orientation = 'RPI'
    anat_reorient.inputs.outputtype = 'NIFTI_GZ'

    workflow.connect(anat_deoblique, 'out_file', anat_reorient, 'in_file')

    resource_pool["anat_reorient"] = (anat_reorient, 'out_file')

    return workflow, resource_pool


def anatomical_skullstrip_workflow(workflow, resource_pool, config, name="_"):
    """Build a Nipype workflow to skullstrip an anatomical image using AFNI's
    3dSkullStrip.

    - If any resources/outputs required by this workflow are not in the
      resource pool, this workflow will call pre-requisite workflow builder
      functions to further populate the pipeline with workflows which will
      calculate/generate these necessary pre-requisites.

    Expected Resources in Resource Pool
      - anatomical_reorient: The deobliqued, reoriented anatomical scan.

    New Resources Added to Resource Pool
      - anatomical_brain: The skull-stripped anatomical image (brain only).

    Workflow Steps
      1. AFNI 3dSkullStrip to create a binary mask selecting only the brain.
      2. AFNI 3dcalc to multiply the anatomical image with this mask.

    :type workflow: Nipype workflow object
    :param workflow: A Nipype workflow object which can already contain other
                     connected nodes; this function will insert the following
                     workflow into this one provided.
    :type resource_pool: dict
    :param resource_pool: A dictionary defining input files and pointers to
                          Nipype node outputs / workflow connections; the keys
                          are the resource names.
    :type config: dict
    :param config: A dictionary defining the configuration settings for the
                   workflow, such as directory paths or toggled options.
    :type name: str
    :param name: (default: "_") A string to append to the end of each node
                 name.
    :rtype: Nipype workflow object
    :return: The Nipype workflow originally provided, but with this function's
              sub-workflow connected into it.
    :rtype: dict
    :return: The resource pool originally provided, but updated (if
             applicable) with the newest outputs and connections.
    """

    import copy
    import nipype.pipeline.engine as pe

    from nipype.interfaces.afni import preprocess

    if "anat_reorient" not in resource_pool.keys():
        from .workflows.anatomical import anatomical_reorient_workflow
        old_rp = copy.copy(resource_pool)
        workflow, new_resource_pool = \
            anatomical_reorient_workflow(workflow, resource_pool, config,
                                         name)
        if resource_pool == old_rp:
            return workflow, resource_pool

    anat_skullstrip = pe.Node(interface=preprocess.SkullStrip(),
                              name='anat_skullstrip%s' % name)
    anat_skullstrip.inputs.outputtype = 'NIFTI_GZ'

    try:
        anat_skullstrip_orig_vol = pe.Node(interface=preprocess.Calc(),
                                           name='anat_skullstrip_orig_vol%s'
                                                % name)
    except AttributeError:
        from nipype.interfaces.afni import utils as afni_utils
        anat_skullstrip_orig_vol = pe.Node(interface=afni_utils.Calc(),
                                           name='anat_skullstrip_orig_vol%s'
                                                % name)

    anat_skullstrip_orig_vol.inputs.expr = 'a*step(b)'
    anat_skullstrip_orig_vol.inputs.outputtype = 'NIFTI_GZ'

    if isinstance(resource_pool["anat_reorient"], tuple):
        node, out_file = resource_pool["anat_reorient"]
        workflow.connect(node, out_file, anat_skullstrip, 'in_file')
    else:
        anat_skullstrip.inputs.in_file = \
            resource_pool["anat_reorient"]

    if isinstance(resource_pool["anat_reorient"], tuple):
        node, out_file = resource_pool["anat_reorient"]
        workflow.connect(node, out_file, anat_skullstrip_orig_vol,
                         'in_file_a')
    else:
        anat_skullstrip_orig_vol.inputs.in_file_a = \
            resource_pool["anat_reorient"]

    workflow.connect(anat_skullstrip, 'out_file',
                     anat_skullstrip_orig_vol, 'in_file_b')

    resource_pool["anat_brain"] = (anat_skullstrip_orig_vol, 'out_file')

    return workflow, resource_pool


def afni_anatomical_linear_registration(workflow, resource_pool,
                                        config, name="_",
                                        in_file="anat_reorient",
                                        ref="anatomical_template"):
    """Build Nipype workflow to calculate the linear registration (participant
    to template) of an anatomical image using AFNI's 3dAllineate.

    - If any resources/outputs required by this workflow are not in the
      resource pool, this workflow will call pre-requisite workflow builder
      functions to further populate the pipeline with workflows which will
      calculate/generate these necessary pre-requisites.

    Expected Settings in Configuration
      - skull_on_registration: (optional- default: True) Whether or not to
                               accept anatomical_reorient or anatomical_brain
                               as the input for registration.
      - template_head_for_anat: (for skull-on registration) The reference
                                template of the whole head.
      - template_brain_for_anat: (for skull-off registration) The reference
                                 template of the brain without skull.

    Expected Resources in Resource Pool
      - anatomical_reorient: The deobliqued, reoriented anatomical scan.
        OR
      - anatomical_brain: The skull-stripped anatomical image (brain only).

    New Resources Added to Resource Pool
      - afni_linear_warped_image: The anatomical image transformed to the
                                  template (using linear warps).
      - allineate_linear_xfm: The text file containing the linear warp matrix
                              produced by AFNI's 3dAllineate.

    Workflow Steps
      1. AFNI's 3dAllineate to calculate the linear registration.

    :type workflow: Nipype workflow object
    :param workflow: A Nipype workflow object which can already contain other
                     connected nodes; this function will insert the following
                     workflow into this one provided.
    :type resource_pool: dict
    :param resource_pool: A dictionary defining input files and pointers to
                          Nipype node outputs / workflow connections; the keys
                          are the resource names.
    :type config: dict
    :param config: A dictionary defining the configuration settings for the
                   workflow, such as directory paths or toggled options.
    :type name: str
    :param name: (default: "_") A string to append to the end of each node
                 name.
    :rtype: Nipype workflow object
    :return: The Nipype workflow originally provided, but with this function's
              sub-workflow connected into it.
    :rtype: dict
    :return: The resource pool originally provided, but updated (if
             applicable) with the newest outputs and connections.
    """

    import copy
    import nipype.pipeline.engine as pe
    from nipype.interfaces.afni import preprocess

    calc_allineate_warp = pe.Node(interface=preprocess.Allineate(),
                                  name='calc_3dAllineate_warp%s' % name)
    calc_allineate_warp.inputs.outputtype = "NIFTI_GZ"

    if in_file == "anat_reorient":
        if "anat_reorient" not in resource_pool.keys():
            from .workflows.anatomical import anatomical_reorient_workflow
            old_rp = copy.copy(resource_pool)
            workflow, new_resource_pool = \
                anatomical_reorient_workflow(workflow, resource_pool,
                                             config, name)
            if resource_pool == old_rp:
                return workflow, resource_pool

    if len(resource_pool[in_file]) == 2:
        node, out_file = resource_pool[in_file]
        workflow.connect(node, out_file, calc_allineate_warp, 'in_file')
    else:
        calc_allineate_warp.inputs.in_file = resource_pool[in_file]

    if ref == "anatomical_template":
        calc_allineate_warp.inputs.reference = config[ref]
    else:
        calc_allineate_warp.inputs.reference = resource_pool[ref]

    calc_allineate_warp.inputs.out_file = "allineate_warped_%s.nii.gz" \
                                          % in_file

    calc_allineate_warp.inputs.out_matrix = "3dallineate_warp"

    if in_file == "anat_reorient":
        resource_pool["anat_linear_xfm"] = \
            (calc_allineate_warp, 'matrix')

    resource_pool["anat_linear_warped_%s" % in_file] = \
        (calc_allineate_warp, 'out_file')

    return workflow, resource_pool


def afni_segmentation_workflow(workflow, resource_pool, config, name="_"):
    """Build a Nipype workflow to generate anatomical tissue segmentation maps
    using AFNI's 3dSeg.

    - If any resources/outputs required by this workflow are not in the
      resource pool, this workflow will call pre-requisite workflow builder
      functions to further populate the pipeline with workflows which will
      calculate/generate these necessary pre-requisites.

    Expected Resources in Resource Pool
      anatomical_brain: The skull-stripped anatomical image (brain only).

    New Resources Added to Resource Pool
      anatomical_csf_mask: The binary mask mapping the CSF voxels.
      anatomical_gm_mask: The binary mask mapping the gray matter voxels.
      anatomical_wm_mask: The binary mask mapping the white matter voxels.

    Workflow Steps
      1. AFNI 3dSeg to run tissue segmentation on the anatomical brain.
      2. AFNI 3dAFNItoNIFTI to convert the AFNI-format 3dSeg output into a
         NIFTI file (as of Oct 2016 3dSeg cannot be configured to write to
         NIFTI).
      3. AFNI 3dcalc to separate the three masks within the output file into
         three separate images.

    :type workflow: Nipype workflow object
    :param workflow: A Nipype workflow object which can already contain other
                     connected nodes; this function will insert the following
                     workflow into this one provided.
    :type resource_pool: dict
    :param resource_pool: A dictionary defining input files and pointers to
                          Nipype node outputs / workflow connections; the keys
                          are the resource names.
    :type config: dict
    :param config: A dictionary defining the configuration settings for the
                   workflow, such as directory paths or toggled options.
    :type name: str
    :param name: (default: "_") A string to append to the end of each node
                 name.
    :rtype: Nipype workflow object
    :return: The Nipype workflow originally provided, but with this function's
              sub-workflow connected into it.
    :rtype: dict
    :return: The resource pool originally provided, but updated (if
             applicable) with the newest outputs and connections.
    """

    import copy
    import nipype.pipeline.engine as pe
    from nipype.interfaces.afni import preprocess

    if "anat_brain" not in resource_pool.keys():
        from .workflows.anatomical import anatomical_skullstrip_workflow
        old_rp = copy.copy(resource_pool)
        workflow, new_resource_pool = \
            anatomical_skullstrip_workflow(workflow, resource_pool, config,
                                           name)
        if resource_pool == old_rp:
            return workflow, resource_pool

    segment = pe.Node(interface=preprocess.Seg(), name='segmentation%s' % name)

    segment.inputs.mask = 'AUTO'

    if isinstance(resource_pool["anat_brain"], tuple):
        node, out_file = resource_pool["anat_brain"]
        workflow.connect(node, out_file, segment, 'in_file')
    else:
        segment.inputs.in_file = resource_pool["anat_brain"]

    # output processing
    try:
        AFNItoNIFTI = pe.Node(interface=preprocess.AFNItoNIFTI(),
                              name="segment_AFNItoNIFTI%s" % name)
    except AttributeError:
        from nipype.interfaces.afni import utils as afni_utils
        AFNItoNIFTI = pe.Node(interface=afni_utils.AFNItoNIFTI(),
                              name="segment_AFNItoNIFTI%s" % name)

    AFNItoNIFTI.inputs.out_file = "classes.nii.gz"

    workflow.connect(segment, 'out_file', AFNItoNIFTI, 'in_file')

    # break out each of the three tissue types into
    # three separate NIFTI files
    try:
        extract_CSF = pe.Node(interface=preprocess.Calc(),
                              name='extract_CSF_mask%s' % name)
        extract_GM = pe.Node(interface=preprocess.Calc(),
                              name='extract_GM_mask%s' % name)
        extract_WM = pe.Node(interface=preprocess.Calc(),
                             name='extract_WM_mask%s' % name)
    except AttributeError:
        from nipype.interfaces.afni import utils as afni_utils
        extract_CSF = pe.Node(interface=afni_utils.Calc(),
                              name='extract_CSF_mask%s' % name)
        extract_GM = pe.Node(interface=afni_utils.Calc(),
                              name='extract_GM_mask%s' % name)
        extract_WM = pe.Node(interface=afni_utils.Calc(),
                             name='extract_WM_mask%s' % name)

    extract_CSF.inputs.expr = "within(a,1,1)"
    extract_CSF.inputs.out_file = "anat_csf_mask.nii.gz"

    extract_GM.inputs.expr = "within(a,2,2)"
    extract_GM.inputs.out_file = "anat_gm_mask.nii.gz"

    extract_WM.inputs.expr = "within(a,3,3)"
    extract_WM.inputs.out_file = "anat_wm_mask.nii.gz"

    workflow.connect(AFNItoNIFTI, 'out_file', extract_CSF, 'in_file_a')
    workflow.connect(AFNItoNIFTI, 'out_file', extract_GM, 'in_file_a')
    workflow.connect(AFNItoNIFTI, 'out_file', extract_WM, 'in_file_a')

    resource_pool["anat_csf_mask"] = (extract_CSF, 'out_file')
    resource_pool["anat_gm_mask"] = (extract_GM, 'out_file')
    resource_pool["anat_wm_mask"] = (extract_WM, 'out_file')

    return workflow, resource_pool