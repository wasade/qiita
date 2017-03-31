# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from unittest import TestCase, main
from tempfile import mkstemp
from os import close, remove, mkdir
from os.path import join, exists, basename
from shutil import rmtree
from datetime import datetime
from functools import partial
from string import punctuation
from tarfile import open as topen

import pandas as pd

from qiita_core.util import qiita_test_checker
import qiita_db as qdb


@qiita_test_checker()
class DBUtilTests(TestCase):
    def setUp(self):
        self.table = 'study'
        self.required = [
            'number_samples_promised', 'study_title', 'mixs_compliant',
            'metadata_complete', 'study_description', 'first_contact',
            'reprocess', 'timeseries_type_id', 'study_alias',
            'study_abstract', 'principal_investigator_id', 'email',
            'number_samples_collected']
        self.files_to_remove = []

    def tearDown(self):
        for fp in self.files_to_remove:
            if exists(fp):
                remove(fp)

    def test_params_dict_to_json(self):
        params_dict = {'opt1': '1', 'opt2': [2, '3'], 3: 9}
        exp = '{"3":9,"opt1":"1","opt2":[2,"3"]}'
        self.assertEqual(qdb.util.params_dict_to_json(params_dict), exp)

    def test_check_required_columns(self):
        # Doesn't do anything if correct info passed, only errors if wrong info
        qdb.util.check_required_columns(self.required, self.table)

    def test_check_required_columns_fail(self):
        self.required.remove('study_title')
        with self.assertRaises(qdb.exceptions.QiitaDBColumnError):
            qdb.util.check_required_columns(self.required, self.table)

    def test_check_table_cols(self):
        # Doesn't do anything if correct info passed, only errors if wrong info
        qdb.util.check_table_cols(self.required, self.table)

    def test_check_table_cols_fail(self):
        self.required.append('BADTHINGNOINHERE')
        with self.assertRaises(qdb.exceptions.QiitaDBColumnError):
            qdb.util.check_table_cols(self.required, self.table)

    def test_get_table_cols(self):
        obs = qdb.util.get_table_cols("qiita_user")
        exp = {"email", "user_level_id", "password", "name", "affiliation",
               "address", "phone", "user_verify_code", "pass_reset_code",
               "pass_reset_timestamp"}
        self.assertEqual(set(obs), exp)

    def test_exists_table(self):
        """Correctly checks if a table exists"""
        # True cases
        self.assertTrue(qdb.util.exists_table("filepath"))
        self.assertTrue(qdb.util.exists_table("qiita_user"))
        self.assertTrue(qdb.util.exists_table("analysis"))
        self.assertTrue(qdb.util.exists_table("prep_1"))
        self.assertTrue(qdb.util.exists_table("sample_1"))
        # False cases
        self.assertFalse(qdb.util.exists_table("sample_2"))
        self.assertFalse(qdb.util.exists_table("prep_3"))
        self.assertFalse(qdb.util.exists_table("foo_table"))
        self.assertFalse(qdb.util.exists_table("bar_table"))

    def test_convert_to_id(self):
        """Tests that ids are returned correctly"""
        self.assertEqual(
            qdb.util.convert_to_id("directory", "filepath_type"), 8)
        self.assertEqual(
            qdb.util.convert_to_id("running", "analysis_status", "status"), 3)
        self.assertEqual(
            qdb.util.convert_to_id("EMP", "portal_type", "portal"), 2)

    def test_convert_to_id_bad_value(self):
        """Tests that ids are returned correctly"""
        with self.assertRaises(qdb.exceptions.QiitaDBLookupError):
            qdb.util.convert_to_id("FAKE", "filepath_type")

    def test_get_artifact_types(self):
        obs = qdb.util.get_artifact_types()
        exp = {'Demultiplexed': 6, 'FASTA_Sanger': 2, 'FASTQ': 3, 'BIOM': 7,
               'per_sample_FASTQ': 5, 'SFF': 1, 'FASTA': 4}
        self.assertEqual(obs, exp)

        obs = qdb.util.get_artifact_types(key_by_id=True)
        exp = {v: k for k, v in exp.items()}
        self.assertEqual(obs, exp)

    def test_get_filepath_types(self):
        """Tests that get_filepath_types works with valid arguments"""
        obs = qdb.util.get_filepath_types()
        exp = {'raw_forward_seqs': 1, 'raw_reverse_seqs': 2,
               'raw_barcodes': 3, 'preprocessed_fasta': 4,
               'preprocessed_fastq': 5, 'preprocessed_demux': 6, 'biom': 7,
               'directory': 8, 'plain_text': 9, 'reference_seqs': 10,
               'reference_tax': 11, 'reference_tree': 12, 'log': 13,
               'sample_template': 14, 'prep_template': 15, 'qiime_map': 16,
               }
        exp = dict(self.conn_handler.execute_fetchall(
            "SELECT filepath_type,filepath_type_id FROM qiita.filepath_type"))
        self.assertEqual(obs, exp)

        obs = qdb.util.get_filepath_types(key='filepath_type_id')
        exp = {v: k for k, v in exp.items()}
        self.assertEqual(obs, exp)

    def test_get_filepath_types_fail(self):
        """Tests that get_Filetypes fails with invalid argument"""
        with self.assertRaises(qdb.exceptions.QiitaDBColumnError):
            qdb.util.get_filepath_types(key='invalid')

    def test_get_data_types(self):
        """Tests that get_data_types works with valid arguments"""
        obs = qdb.util.get_data_types()
        exp = {'16S': 1, '18S': 2, 'ITS': 3, 'Proteomic': 4, 'Metabolomic': 5,
               'Metagenomic': 6}
        self.assertEqual(obs, exp)

        obs = qdb.util.get_data_types(key='data_type_id')
        exp = {v: k for k, v in exp.items()}
        self.assertEqual(obs, exp)

    def test_create_rand_string(self):
        set_punct = set(punctuation)

        obs = qdb.util.create_rand_string(200)
        self.assertEqual(len(obs), 200)
        self.assertTrue(set_punct.intersection(set(obs)))

        obs = qdb.util.create_rand_string(400, punct=False)
        self.assertEqual(len(obs), 400)
        self.assertFalse(set_punct.intersection(set(obs)))

    def test_get_count(self):
        """Checks that get_count retrieves proper count"""
        self.assertEqual(qdb.util.get_count('qiita.study_person'), 3)

    def test_check_count(self):
        """Checks that check_count returns True and False appropriately"""
        self.assertTrue(qdb.util.check_count('qiita.study_person', 3))
        self.assertFalse(qdb.util.check_count('qiita.study_person', 2))

    def test_insert_filepaths(self):
        fd, fp = mkstemp()
        close(fd)
        with open(fp, "w") as f:
            f.write("\n")
        self.files_to_remove.append(fp)

        exp_new_id = 1 + self.conn_handler.execute_fetchone(
            "SELECT last_value FROM qiita.filepath_filepath_id_seq")[0]
        obs = qdb.util.insert_filepaths([(fp, 1)], 2, "raw_data", "filepath")
        self.assertEqual(obs, [exp_new_id])

        # Check that the files have been copied correctly
        exp_fp = join(qdb.util.get_db_files_base_dir(), "raw_data",
                      "2_%s" % basename(fp))
        self.assertTrue(exists(exp_fp))
        self.assertFalse(exists(fp))
        self.files_to_remove.append(exp_fp)

        # Check that the filepaths have been added to the DB
        obs = self.conn_handler.execute_fetchall(
            "SELECT * FROM qiita.filepath WHERE filepath_id=%d" % exp_new_id)
        exp_fp = "2_%s" % basename(fp)
        exp = [[exp_new_id, exp_fp, 1, '852952723', 1, 5]]
        self.assertEqual(obs, exp)

        qdb.util.purge_filepaths()

    def test_insert_filepaths_copy(self):
        fd, fp = mkstemp()
        close(fd)
        with open(fp, "w") as f:
            f.write("\n")
        self.files_to_remove.append(fp)

        # The id's in the database are bigserials, i.e. they get
        # autoincremented for each element introduced.
        exp_new_id = 1 + self.conn_handler.execute_fetchone(
            "SELECT last_value FROM qiita.filepath_filepath_id_seq")[0]
        obs = qdb.util.insert_filepaths([(fp, 1)], 2, "raw_data", "filepath",
                                        copy=True)
        self.assertEqual(obs, [exp_new_id])

        # Check that the files have been copied correctly
        exp_fp = join(qdb.util.get_db_files_base_dir(), "raw_data",
                      "2_%s" % basename(fp))
        self.assertTrue(exists(exp_fp))
        self.assertTrue(exists(fp))
        self.files_to_remove.append(exp_fp)

        # Check that the filepaths have been added to the DB
        obs = self.conn_handler.execute_fetchall(
            "SELECT * FROM qiita.filepath WHERE filepath_id=%d" % exp_new_id)
        exp_fp = "2_%s" % basename(fp)
        exp = [[exp_new_id, exp_fp, 1, '852952723', 1, 5]]
        self.assertEqual(obs, exp)

        qdb.util.purge_filepaths()

    def test_insert_filepaths_string(self):
        fd, fp = mkstemp()
        close(fd)
        with open(fp, "w") as f:
            f.write("\n")
        self.files_to_remove.append(fp)

        exp_new_id = 1 + self.conn_handler.execute_fetchone(
            "SELECT last_value FROM qiita.filepath_filepath_id_seq")[0]
        obs = qdb.util.insert_filepaths(
            [(fp, "raw_forward_seqs")], 2, "raw_data", "filepath")
        self.assertEqual(obs, [exp_new_id])

        # Check that the files have been copied correctly
        exp_fp = join(qdb.util.get_db_files_base_dir(), "raw_data",
                      "2_%s" % basename(fp))
        self.assertTrue(exists(exp_fp))
        self.files_to_remove.append(exp_fp)

        # Check that the filepaths have been added to the DB
        obs = self.conn_handler.execute_fetchall(
            "SELECT * FROM qiita.filepath WHERE filepath_id=%d" % exp_new_id)
        exp_fp = "2_%s" % basename(fp)
        exp = [[exp_new_id, exp_fp, 1, '852952723', 1, 5]]
        self.assertEqual(obs, exp)

        qdb.util.purge_filepaths()

    def test_retrieve_filepaths(self):
        obs = qdb.util.retrieve_filepaths('artifact_filepath',
                                          'artifact_id', 1)
        path_builder = partial(
            join, qdb.util.get_db_files_base_dir(), "raw_data")
        exp = [(1, path_builder("1_s_G1_L001_sequences.fastq.gz"),
                "raw_forward_seqs"),
               (2, path_builder("1_s_G1_L001_sequences_barcodes.fastq.gz"),
                "raw_barcodes")]
        self.assertEqual(obs, exp)

    def test_retrieve_filepaths_sort(self):
        obs = qdb.util.retrieve_filepaths(
            'artifact_filepath', 'artifact_id', 1, sort='descending')
        path_builder = partial(
            join, qdb.util.get_db_files_base_dir(), "raw_data")
        exp = [(2, path_builder("1_s_G1_L001_sequences_barcodes.fastq.gz"),
                "raw_barcodes"),
               (1, path_builder("1_s_G1_L001_sequences.fastq.gz"),
                "raw_forward_seqs")]
        self.assertEqual(obs, exp)

    def test_retrieve_filepaths_type(self):
        obs = qdb.util.retrieve_filepaths(
            'artifact_filepath', 'artifact_id', 1, sort='descending',
            fp_type='raw_barcodes')
        path_builder = partial(
            join, qdb.util.get_db_files_base_dir(), "raw_data")
        exp = [(2, path_builder("1_s_G1_L001_sequences_barcodes.fastq.gz"),
                "raw_barcodes")]
        self.assertEqual(obs, exp)

        obs = qdb.util.retrieve_filepaths(
            'artifact_filepath', 'artifact_id', 1, fp_type='raw_barcodes')
        path_builder = partial(
            join, qdb.util.get_db_files_base_dir(), "raw_data")
        exp = [(2, path_builder("1_s_G1_L001_sequences_barcodes.fastq.gz"),
                "raw_barcodes")]
        self.assertEqual(obs, exp)

        obs = qdb.util.retrieve_filepaths(
            'artifact_filepath', 'artifact_id', 1, fp_type='biom')
        path_builder = partial(
            join, qdb.util.get_db_files_base_dir(), "raw_data")
        self.assertEqual(obs, [])

    def test_retrieve_filepaths_error(self):
        with self.assertRaises(qdb.exceptions.QiitaDBError):
            qdb.util.retrieve_filepaths('artifact_filepath', 'artifact_id', 1,
                                        sort='Unknown')

    def _common_purge_filpeaths_test(self):
        # Get all the filepaths so we can test if they've been removed or not
        sql_fp = "SELECT filepath, data_directory_id FROM qiita.filepath"
        fps = [join(qdb.util.get_mountpoint_path_by_id(dd_id), fp)
               for fp, dd_id in self.conn_handler.execute_fetchall(sql_fp)]

        # Make sure that the files exist - specially for travis
        for fp in fps:
            if not exists(fp):
                with open(fp, 'w') as f:
                    f.write('\n')
                self.files_to_remove.append(fp)

        _, raw_data_mp = qdb.util.get_mountpoint('raw_data')[0]

        removed_fps = [
            join(raw_data_mp, '2_sequences_barcodes.fastq.gz'),
            join(raw_data_mp, '2_sequences.fastq.gz')]

        for fp in removed_fps:
            with open(fp, 'w') as f:
                f.write('\n')

        sql = """INSERT INTO qiita.filepath
                    (filepath, filepath_type_id, checksum,
                     checksum_algorithm_id, data_directory_id)
                VALUES ('2_sequences_barcodes.fastq.gz', 3, '852952723', 1, 5),
                       ('2_sequences.fastq.gz', 1, '852952723', 1, 5)
                RETURNING filepath_id"""
        fp_ids = self.conn_handler.execute_fetchall(sql)

        fps = set(fps).difference(removed_fps)

        # Check that the files exist
        for fp in fps:
            self.assertTrue(exists(fp))
        for fp in removed_fps:
            self.assertTrue(exists(fp))

        exp_count = qdb.util.get_count("qiita.filepath") - 2

        qdb.util.purge_filepaths()

        obs_count = qdb.util.get_count("qiita.filepath")

        # Check that only 2 rows have been removed
        self.assertEqual(obs_count, exp_count)

        # Check that the 2 rows that have been removed are the correct ones
        sql = """SELECT EXISTS(
                    SELECT * FROM qiita.filepath WHERE filepath_id = %s)"""
        obs = self.conn_handler.execute_fetchone(sql, (fp_ids[0][0],))[0]
        self.assertFalse(obs)
        obs = self.conn_handler.execute_fetchone(sql, (fp_ids[1][0],))[0]
        self.assertFalse(obs)

        # Check that the files have been successfully removed
        for fp in removed_fps:
            self.assertFalse(exists(fp))

        # Check that all the other files still exist
        for fp in fps:
            self.assertTrue(exists(fp))

    def test_purge_filepaths(self):
        self._common_purge_filpeaths_test()

    def test_empty_trash_upload_folder(self):
        # creating file to delete so we know it actually works
        study_id = '1'
        uploads_fp = join(qdb.util.get_mountpoint("uploads")[0][1], study_id)
        trash = join(uploads_fp, 'trash')
        if not exists(trash):
            mkdir(trash)
        fp = join(trash, 'my_file_to_delete.txt')
        open(fp, 'w').close()

        self.assertTrue(exists(fp))
        qdb.util.empty_trash_upload_folder()
        self.assertFalse(exists(fp))

    def test_purge_filepaths_null_cols(self):
        # For more details about the source of the issue that motivates this
        # test: http://www.depesz.com/2008/08/13/nulls-vs-not-in/
        # In the current set up, the only place where we can actually have a
        # null value in a filepath id is in the reference table. Add a new
        # reference without tree and taxonomy:
        fd, seqs_fp = mkstemp(suffix="_seqs.fna")
        close(fd)
        ref = qdb.reference.Reference.create("null_db", "13_2", seqs_fp)
        self.files_to_remove.append(ref.sequence_fp)

        self._common_purge_filpeaths_test()

    def test_move_filepaths_to_upload_folder(self):
        # setting up test, done here as this is the only test that uses these
        # files
        fd, seqs_fp = mkstemp(suffix='_seqs.fastq')
        close(fd)
        fd, html_fp = mkstemp(suffix='.html')
        close(fd)
        st = qdb.study.Study(1)
        metadata_dict = {
            'SKB8.640193': {'center_name': 'ANL',
                            'primer': 'GTGCCAGCMGCCGCGGTAA',
                            'barcode': 'GTCCGCAAGTTA',
                            'run_prefix': "s_G1_L001_sequences",
                            'platform': 'ILLUMINA',
                            'instrument_model': 'Illumina MiSeq',
                            'library_construction_protocol': 'AAAA',
                            'experiment_design_description': 'BBBB'}}
        metadata = pd.DataFrame.from_dict(metadata_dict, orient='index',
                                          dtype=str)
        pt = qdb.metadata_template.prep_template.PrepTemplate.create(
            metadata, qdb.study.Study(1), "16S")

        artifact = qdb.artifact.Artifact.create(
            [(seqs_fp, 1), (html_fp, 'html_summary')], "FASTQ",
            prep_template=pt)
        filepaths = artifact.filepaths
        # deleting reference so we can directly call
        # move_filepaths_to_upload_folder
        for fid, _, _ in filepaths:
            sql = "DELETE FROM qiita.artifact_filepath WHERE filepath_id=%s"
            self.conn_handler.execute(sql, (fid,))

        # moving filepaths
        qdb.util.move_filepaths_to_upload_folder(st.id, filepaths)

        # check that they do not exist in the old path but do in the new one
        path_for_removal = join(qdb.util.get_mountpoint("uploads")[0][1],
                                str(st.id))
        for _, fp, fp_type in filepaths:
            self.assertFalse(exists(fp))
            new_fp = join(path_for_removal, basename(fp))
            if fp_type == 'html_summary':
                # The html summary gets removed, not moved
                self.assertFalse(exists(new_fp))
            else:
                self.assertTrue(exists(new_fp))

            self.files_to_remove.append(new_fp)

    def test_get_filepath_id(self):
        _, base = qdb.util.get_mountpoint("raw_data")[0]
        fp = join(base, '1_s_G1_L001_sequences.fastq.gz')
        obs = qdb.util.get_filepath_id("raw_data", fp)
        self.assertEqual(obs, 1)

    def test_get_filepath_id_error(self):
        with self.assertRaises(qdb.exceptions.QiitaDBError):
            qdb.util.get_filepath_id("raw_data", "Not_a_path")

    def test_get_mountpoint(self):
        exp = [(5, join(qdb.util.get_db_files_base_dir(), 'raw_data'))]
        obs = qdb.util.get_mountpoint("raw_data")
        self.assertEqual(obs, exp)

        exp = [(1, join(qdb.util.get_db_files_base_dir(), 'analysis'))]
        obs = qdb.util.get_mountpoint("analysis")
        self.assertEqual(obs, exp)

        exp = [(2, join(qdb.util.get_db_files_base_dir(), 'job'))]
        obs = qdb.util.get_mountpoint("job")
        self.assertEqual(obs, exp)

        # inserting new ones so we can test that it retrieves these and
        # doesn't alter other ones
        self.conn_handler.execute(
            "UPDATE qiita.data_directory SET active=false WHERE "
            "data_directory_id=1")
        count = qdb.util.get_count('qiita.data_directory')
        sql = """INSERT INTO qiita.data_directory (data_type, mountpoint,
                                                   subdirectory, active)
                 VALUES ('analysis', 'analysis_tmp', true, true),
                        ('raw_data', 'raw_data_tmp', true, false)"""
        self.conn_handler.execute(sql)

        # this should have been updated
        exp = [(count + 1, join(qdb.util.get_db_files_base_dir(),
                'analysis_tmp'))]
        obs = qdb.util.get_mountpoint("analysis")
        self.assertEqual(obs, exp)

        # these 2 shouldn't
        exp = [(5, join(qdb.util.get_db_files_base_dir(), 'raw_data'))]
        obs = qdb.util.get_mountpoint("raw_data")
        self.assertEqual(obs, exp)

        exp = [(2, join(qdb.util.get_db_files_base_dir(), 'job'))]
        obs = qdb.util.get_mountpoint("job")
        self.assertEqual(obs, exp)

        # testing multi returns
        exp = [(5, join(qdb.util.get_db_files_base_dir(), 'raw_data')),
               (count + 2, join(qdb.util.get_db_files_base_dir(),
                'raw_data_tmp'))]
        obs = qdb.util.get_mountpoint("raw_data", retrieve_all=True)
        self.assertEqual(obs, exp)

        # testing retrieve subdirectory
        exp = [
            (5, join(qdb.util.get_db_files_base_dir(), 'raw_data'), False),
            (count + 2, join(qdb.util.get_db_files_base_dir(), 'raw_data_tmp'),
             True)]
        obs = qdb.util.get_mountpoint("raw_data", retrieve_all=True,
                                      retrieve_subdir=True)
        self.assertEqual(obs, exp)

    def test_get_mountpoint_path_by_id(self):
        exp = join(qdb.util.get_db_files_base_dir(), 'raw_data')
        obs = qdb.util.get_mountpoint_path_by_id(5)
        self.assertEqual(obs, exp)

        exp = join(qdb.util.get_db_files_base_dir(), 'analysis')
        obs = qdb.util.get_mountpoint_path_by_id(1)
        self.assertEqual(obs, exp)

        exp = join(qdb.util.get_db_files_base_dir(), 'job')
        obs = qdb.util.get_mountpoint_path_by_id(2)
        self.assertEqual(obs, exp)

        # inserting new ones so we can test that it retrieves these and
        # doesn't alter other ones
        self.conn_handler.execute(
            "UPDATE qiita.data_directory SET active=false WHERE "
            "data_directory_id=1")
        count = qdb.util.get_count('qiita.data_directory')
        sql = """INSERT INTO qiita.data_directory (data_type, mountpoint,
                                                   subdirectory, active)
                 VALUES ('analysis', 'analysis_tmp', true, true),
                        ('raw_data', 'raw_data_tmp', true, false)"""
        self.conn_handler.execute(sql)

        # this should have been updated
        exp = join(qdb.util.get_db_files_base_dir(), 'analysis_tmp')
        obs = qdb.util.get_mountpoint_path_by_id(count + 1)
        self.assertEqual(obs, exp)

        # these 2 shouldn't
        exp = join(qdb.util.get_db_files_base_dir(), 'raw_data')
        obs = qdb.util.get_mountpoint_path_by_id(5)
        self.assertEqual(obs, exp)

        exp = join(qdb.util.get_db_files_base_dir(), 'job')
        obs = qdb.util.get_mountpoint_path_by_id(2)
        self.assertEqual(obs, exp)

    def test_get_files_from_uploads_folders(self):
        # something has been uploaded and ignoring hidden files/folders
        # and folders
        exp = [(7, 'uploaded_file.txt')]
        obs = qdb.util.get_files_from_uploads_folders("1")
        self.assertEqual(obs, exp)

        # nothing has been uploaded
        exp = []
        obs = qdb.util.get_files_from_uploads_folders("2")
        self.assertEqual(obs, exp)

    def test_move_upload_files_to_trash(self):
        test_filename = 'this_is_a_test_file.txt'

        # create file to move to trash
        fid, folder = qdb.util.get_mountpoint("uploads")[0]
        test_fp = join(folder, '1', test_filename)
        with open(test_fp, 'w') as f:
            f.write('test')

        self.files_to_remove.append(test_fp)

        exp = [(fid, 'this_is_a_test_file.txt'), (fid, 'uploaded_file.txt')]
        obs = qdb.util.get_files_from_uploads_folders("1")
        self.assertItemsEqual(obs, exp)

        # move file
        qdb.util.move_upload_files_to_trash(1, [(fid, test_filename)])
        exp = [(fid, 'uploaded_file.txt')]
        obs = qdb.util.get_files_from_uploads_folders("1")
        self.assertItemsEqual(obs, exp)

        # testing errors
        with self.assertRaises(qdb.exceptions.QiitaDBError):
            qdb.util.move_upload_files_to_trash(2, [(fid, test_filename)])
        with self.assertRaises(qdb.exceptions.QiitaDBError):
            qdb.util.move_upload_files_to_trash(1, [(10, test_filename)])
        with self.assertRaises(qdb.exceptions.QiitaDBError):
            qdb.util.move_upload_files_to_trash(1, [(fid, test_filename)])

        # removing trash folder
        rmtree(join(folder, '1', 'trash'))

    def test_get_environmental_packages(self):
        obs = qdb.util.get_environmental_packages()
        exp = [['air', 'ep_air'],
               ['built environment', 'ep_built_environment'],
               ['host-associated', 'ep_host_associated'],
               ['human-amniotic-fluid', 'ep_human_amniotic_fluid'],
               ['human-associated', 'ep_human_associated'],
               ['human-blood', 'ep_human_blood'],
               ['human-gut', 'ep_human_gut'],
               ['human-oral', 'ep_human_oral'],
               ['human-skin', 'ep_human_skin'],
               ['human-urine', 'ep_human_urine'],
               ['human-vaginal', 'ep_human_vaginal'],
               ['microbial mat/biofilm', 'ep_microbial_mat_biofilm'],
               ['miscellaneous natural or artificial environment',
                'ep_misc_artif'],
               ['plant-associated', 'ep_plant_associated'],
               ['sediment', 'ep_sediment'],
               ['soil', 'ep_soil'],
               ['wastewater/sludge', 'ep_wastewater_sludge'],
               ['water', 'ep_water']]
        self.assertEqual(sorted(obs), sorted(exp))

    def test_get_timeseries_types(self):
        obs = qdb.util.get_timeseries_types()
        exp = [[1, 'None', 'None'],
               [2, 'real', 'single intervention'],
               [3, 'real', 'multiple intervention'],
               [4, 'real', 'combo intervention'],
               [5, 'pseudo', 'single intervention'],
               [6, 'pseudo', 'multiple intervention'],
               [7, 'pseudo', 'combo intervention'],
               [8, 'mixed', 'single intervention'],
               [9, 'mixed', 'multiple intervention'],
               [10, 'mixed', 'combo intervention']]
        self.assertEqual(obs, exp)

    def test_filepath_id_to_rel_path(self):
        obs = qdb.util.filepath_id_to_rel_path(1)
        exp = 'raw_data/1_s_G1_L001_sequences.fastq.gz'
        self.assertEqual(obs, exp)

        obs = qdb.util.filepath_id_to_rel_path(3)
        exp = 'preprocessed_data/1_seqs.fna'
        self.assertEqual(obs, exp)

        fd, fp = mkstemp()
        close(fd)
        with open(fp, 'w') as f:
            f.write('\n')
        self.files_to_remove.append(fp)
        test = qdb.util.insert_filepaths(
            [(fp, "raw_forward_seqs")], 2, "FASTQ", "filepath")[0]
        with qdb.sql_connection.TRN:
            sql = """INSERT INTO qiita.artifact_filepath
                            (artifact_id, filepath_id)
                        VALUES (%s, %s)"""
            qdb.sql_connection.TRN.add(sql, [2, test])
            qdb.sql_connection.TRN.execute()

        obs = qdb.util.filepath_id_to_rel_path(test)
        exp = 'FASTQ/2/%s' % basename(fp)
        self.assertEqual(obs, exp)

    def test_filepath_ids_to_rel_paths(self):
        fd, fp = mkstemp()
        close(fd)
        with open(fp, 'w') as f:
            f.write('\n')
        self.files_to_remove.append(fp)
        test = qdb.util.insert_filepaths(
            [(fp, "raw_forward_seqs")], 2, "FASTQ", "filepath")[0]
        with qdb.sql_connection.TRN:
            sql = """INSERT INTO qiita.artifact_filepath
                            (artifact_id, filepath_id)
                        VALUES (%s, %s)"""
            qdb.sql_connection.TRN.add(sql, [2, test])
            qdb.sql_connection.TRN.execute()

        obs = qdb.util.filepath_ids_to_rel_paths([1, 3, test])
        exp = {1: 'raw_data/1_s_G1_L001_sequences.fastq.gz',
               3: 'preprocessed_data/1_seqs.fna',
               test: 'FASTQ/2/%s' % basename(fp)}

        self.assertEqual(obs, exp)

    def test_check_access_to_analysis_result(self):
        obs = qdb.util.check_access_to_analysis_result('test@foo.bar',
                                                       '1_job_result.txt')
        exp = [13]

        self.assertEqual(obs, exp)

    def test_add_message(self):
        count = qdb.util.get_count('qiita.message') + 1
        user = qdb.user.User.create('new@test.bar', 'password')
        users = [user]
        qdb.util.add_message("TEST MESSAGE", users)

        obs = [[x[0], x[1]] for x in user.messages()]
        exp = [[count, 'TEST MESSAGE']]
        self.assertEqual(obs, exp)

    def test_add_system_message(self):
        count = qdb.util.get_count('qiita.message') + 1
        qdb.util.add_system_message("SYS MESSAGE",
                                    datetime(2015, 8, 5, 19, 41))

        obs = [[x[0], x[1]]
               for x in qdb.user.User('shared@foo.bar').messages()]
        exp = [[count, 'SYS MESSAGE'], [1, 'message 1']]
        self.assertEqual(obs, exp)
        obs = [[x[0], x[1]] for x in qdb.user.User('admin@foo.bar').messages()]
        exp = [[count, 'SYS MESSAGE']]
        self.assertEqual(obs, exp)

        sql = "SELECT expiration from qiita.message WHERE message_id = %s"
        obs = self.conn_handler.execute_fetchall(sql, [count])
        exp = [[datetime(2015, 8, 5, 19, 41)]]
        self.assertEqual(obs, exp)

    def test_clear_system_messages(self):
        message_id = qdb.util.get_count('qiita.message') + 1
        user = qdb.user.User.create('csm@test.bar', 'password')
        obs = [[x[0], x[1]] for x in user.messages()]
        exp = []
        self.assertEqual(obs, exp)

        qdb.util.add_system_message("SYS MESSAGE",
                                    datetime(2015, 8, 5, 19, 41))
        obs = [[x[0], x[1]] for x in user.messages()]
        exp = [[message_id, 'SYS MESSAGE']]
        self.assertItemsEqual(obs, exp)

        qdb.util.clear_system_messages()
        obs = [[x[0], x[1]] for x in user.messages()]
        exp = []
        self.assertEqual(obs, exp)

        # Run again with no system messages to make sure no errors
        qdb.util.clear_system_messages()

    def test_supported_filepath_types(self):
        obs = qdb.util.supported_filepath_types("FASTQ")
        exp = [["raw_forward_seqs", True], ["raw_reverse_seqs", False],
               ["raw_barcodes", True]]
        self.assertItemsEqual(obs, exp)

        obs = qdb.util.supported_filepath_types("BIOM")
        exp = [["biom", True], ["directory", False], ["log", False]]
        self.assertItemsEqual(obs, exp)

    def test_generate_biom_and_metadata_release(self):
        tgz, txt = qdb.util.generate_biom_and_metadata_release('private')
        self.files_to_remove.extend([tgz, txt])

        tmp = topen(tgz, "r:gz")
        tgz_obs = [ti.name for ti in tmp]
        tmp.close()
        # files names might change due to updates and patches so just check
        # that the prefix exists.
        fn = 'processed_data/1_study_1001_closed_reference_otu_table.biom'
        self.assertTrue(fn in tgz_obs)
        tgz_obs.remove(fn)
        # yes, this file is there twice
        self.assertTrue(fn in tgz_obs)
        tgz_obs.remove(fn)
        # let's check the next biom
        fn = ('processed_data/1_study_1001_closed_reference_otu_table_Silva.'
              'biom')
        self.assertTrue(fn in tgz_obs)
        tgz_obs.remove(fn)
        # now let's check prep info files based on their suffix, just take
        # the first one and check/rm the occurances of that file
        fn_prep = [f for f in tgz_obs
                   if f.startswith('templates/1_prep_1_')][0]
        # 3 times
        self.assertTrue(fn_prep in tgz_obs)
        tgz_obs.remove(fn_prep)
        self.assertTrue(fn_prep in tgz_obs)
        tgz_obs.remove(fn_prep)
        self.assertTrue(fn_prep in tgz_obs)
        tgz_obs.remove(fn_prep)
        fn_sample = [f for f in tgz_obs if f.startswith('templates/1_')][0]
        # 3 times
        self.assertTrue(fn_sample in tgz_obs)
        tgz_obs.remove(fn_sample)
        self.assertTrue(fn_sample in tgz_obs)
        tgz_obs.remove(fn_sample)
        self.assertTrue(fn_sample in tgz_obs)
        tgz_obs.remove(fn_sample)
        # now it should be empty
        self.assertEqual(tgz_obs, [])

        tmp = open(txt)
        txt_obs = tmp.readlines()
        tmp.close()
        txt_exp = [
            'biom_fp\tsample_fp\tprep_fp\tqiita_artifact_id\tcommand\n',
            'processed_data/1_study_1001_closed_reference_otu_table.biom\t'
            '%s\t%s\t4\tPick closed-reference OTUs, Split libraries FASTQ\n'
            % (fn_sample, fn_prep),
            'processed_data/1_study_1001_closed_reference_otu_table.biom\t'
            '%s\t%s\t5\tPick closed-reference OTUs, Split libraries FASTQ\n'
            % (fn_sample, fn_prep),
            'processed_data/1_study_1001_closed_reference_otu_table_Silva.bio'
            'm\t%s\t%s\t6\tPick closed-reference OTUs, Split libraries FASTQ\n'
            % (fn_sample, fn_prep)]
        self.assertEqual(txt_obs, txt_exp)

        # whatever the configuration was, we will change to settings so we can
        # test the other option when dealing with the end '/'
        with qdb.sql_connection.TRN:
            qdb.sql_connection.TRN.add(
                "SELECT base_data_dir FROM settings")
            obdr = qdb.sql_connection.TRN.execute_fetchlast()
            if obdr[-1] == '/':
                bdr = obdr[:-1]
            else:
                bdr = obdr + '/'

            qdb.sql_connection.TRN.add(
                "UPDATE settings SET base_data_dir = '%s'" % bdr)
            bdr = qdb.sql_connection.TRN.execute()

        tgz, txt = qdb.util.generate_biom_and_metadata_release('private')
        self.files_to_remove.extend([tgz, txt])

        tmp = topen(tgz, "r:gz")
        tgz_obs = [ti.name for ti in tmp]
        tmp.close()
        # files names might change due to updates and patches so just check
        # that the prefix exists.
        fn = 'processed_data/1_study_1001_closed_reference_otu_table.biom'
        self.assertTrue(fn in tgz_obs)
        tgz_obs.remove(fn)
        # yes, this file is there twice
        self.assertTrue(fn in tgz_obs)
        tgz_obs.remove(fn)
        # let's check the next biom
        fn = ('processed_data/1_study_1001_closed_reference_otu_table_Silva.'
              'biom')
        self.assertTrue(fn in tgz_obs)
        tgz_obs.remove(fn)
        # now let's check prep info files based on their suffix, just take
        # the first one and check/rm the occurances of that file
        fn_prep = [f for f in tgz_obs
                   if f.startswith('templates/1_prep_1_')][0]
        # 3 times
        self.assertTrue(fn_prep in tgz_obs)
        tgz_obs.remove(fn_prep)
        self.assertTrue(fn_prep in tgz_obs)
        tgz_obs.remove(fn_prep)
        self.assertTrue(fn_prep in tgz_obs)
        tgz_obs.remove(fn_prep)
        fn_sample = [f for f in tgz_obs if f.startswith('templates/1_')][0]
        # 3 times
        self.assertTrue(fn_sample in tgz_obs)
        tgz_obs.remove(fn_sample)
        self.assertTrue(fn_sample in tgz_obs)
        tgz_obs.remove(fn_sample)
        self.assertTrue(fn_sample in tgz_obs)
        tgz_obs.remove(fn_sample)
        # now it should be empty
        self.assertEqual(tgz_obs, [])

        tmp = open(txt)
        txt_obs = tmp.readlines()
        tmp.close()
        txt_exp = [
            'biom_fp\tsample_fp\tprep_fp\tqiita_artifact_id\tcommand\n',
            'processed_data/1_study_1001_closed_reference_otu_table.biom\t'
            '%s\t%s\t4\tPick closed-reference OTUs, Split libraries FASTQ\n'
            % (fn_sample, fn_prep),
            'processed_data/1_study_1001_closed_reference_otu_table.biom\t'
            '%s\t%s\t5\tPick closed-reference OTUs, Split libraries FASTQ\n'
            % (fn_sample, fn_prep),
            'processed_data/1_study_1001_closed_reference_otu_table_Silva.bio'
            'm\t%s\t%s\t6\tPick closed-reference OTUs, Split libraries FASTQ\n'
            % (fn_sample, fn_prep)]
        self.assertEqual(txt_obs, txt_exp)

        # returning configuration
        with qdb.sql_connection.TRN:
                    qdb.sql_connection.TRN.add(
                        "UPDATE settings SET base_data_dir = '%s'" % obdr)
                    bdr = qdb.sql_connection.TRN.execute()


@qiita_test_checker()
class UtilTests(TestCase):
    """Tests for the util functions that do not need to access the DB"""

    def setUp(self):
        fh, self.filepath = mkstemp()
        close(fh)
        with open(self.filepath, "w") as f:
            f.write("Some text so we can actually compute a checksum")

    def test_compute_checksum(self):
        """Correctly returns the file checksum"""
        obs = qdb.util.compute_checksum(self.filepath)
        exp = 1719580229
        self.assertEqual(obs, exp)

    def test_scrub_data_nothing(self):
        """Returns the same string without changes"""
        self.assertEqual(qdb.util.scrub_data("nothing_changes"),
                         "nothing_changes")

    def test_scrub_data_semicolon(self):
        """Correctly removes the semicolon from the string"""
        self.assertEqual(qdb.util.scrub_data("remove_;_char"), "remove__char")

    def test_scrub_data_single_quote(self):
        """Correctly removes single quotes from the string"""
        self.assertEqual(qdb.util.scrub_data("'quotes'"), "quotes")

    def test_get_visibilities(self):
        obs = qdb.util.get_visibilities()
        exp = ['awaiting_approval', 'sandbox', 'private', 'public']
        self.assertEqual(obs, exp)

    def test_infer_status(self):
        obs = qdb.util.infer_status([])
        self.assertEqual(obs, 'sandbox')

        obs = qdb.util.infer_status([['private']])
        self.assertEqual(obs, 'private')

        obs = qdb.util.infer_status([['private'], ['public']])
        self.assertEqual(obs, 'public')

        obs = qdb.util.infer_status([['sandbox'], ['awaiting_approval']])
        self.assertEqual(obs, 'awaiting_approval')

        obs = qdb.util.infer_status([['sandbox'], ['sandbox']])
        self.assertEqual(obs, 'sandbox')

    def test_get_pubmed_ids_from_dois(self):
        exp = {'10.100/123456': '123456'}
        obs = qdb.util.get_pubmed_ids_from_dois(['', '10.100/123456'])
        self.assertEqual(obs, exp)

    def test_generate_study_list(self):
        exp_info = [{
            'metadata_complete': True,
            'ebi_submission_status': 'submitted',
            'shared': [('shared@foo.bar', 'Shared')],
            'pi': ('PI_dude@foo.bar', 'PIDude'),
            'status': 'private',
            'proc_data_info': [],
            'publication_doi': ['10.100/123456', '10.100/7891011'],
            'publication_pid': ['123456', '7891011'],
            'study_abstract': (
                'This is a preliminary study to examine the microbiota '
                'associated with the Cannabis plant. Soils samples from '
                'the bulk soil, soil associated with the roots, and the '
                'rhizosphere were extracted and the DNA sequenced. Roots '
                'from three independent plants of different strains were '
                'examined. These roots were obtained November 11, 2011 from '
                'plants that had been harvested in the summer. Future studies '
                'will attempt to analyze the soils and rhizospheres from the '
                'same location at different time points in the plant '
                'lifecycle.'),
            'study_id': 1,
            'ebi_study_accession': 'EBI123456-BB',
            'study_title': ('Identification of the Microbiomes for Cannabis '
                            'Soils'),
            'number_samples_collected': 27,
            'study_tags': None
        }]
        obs_info = qdb.util.generate_study_list([1, 2, 3, 4], False)
        self.assertEqual(obs_info, exp_info)

        qdb.artifact.Artifact(4).visibility = 'public'
        exp_info[0]['status'] = 'public'
        exp_info[0]['proc_data_info'] = [{
            'data_type': '18S',
            'algorithm': 'QIIME (Pick closed-reference OTUs)',
            'pid': 4,
            'processed_date': '2012-10-02 17:30:00',
            'params': {
                'similarity': 0.97,
                'reference_name': 'Greengenes',
                'sortmerna_e_value': 1,
                'sortmerna_max_pos': 10000,
                'threads': 1,
                'sortmerna_coverage': 0.97,
                'reference_version': '13_8'},
            'samples': ['1.SKB1.640202', '1.SKB2.640194', '1.SKB3.640195',
                        '1.SKB4.640189', '1.SKB5.640181', '1.SKB6.640176',
                        '1.SKB7.640196', '1.SKB8.640193', '1.SKB9.640200',
                        '1.SKD1.640179', '1.SKD2.640178', '1.SKD3.640198',
                        '1.SKD4.640185', '1.SKD5.640186', '1.SKD6.640190',
                        '1.SKD7.640191', '1.SKD8.640184', '1.SKD9.640182',
                        '1.SKM1.640183', '1.SKM2.640199', '1.SKM3.640197',
                        '1.SKM4.640180', '1.SKM5.640177', '1.SKM6.640187',
                        '1.SKM7.640188', '1.SKM8.640201', '1.SKM9.640192']}]
        obs_info = qdb.util.generate_study_list([1, 2, 3, 4], True,
                                                public_only=True)
        self.assertEqual(obs_info, exp_info)

        exp_info[0]['proc_data_info'].extend(
           [{
            'data_type': '18S',
            'algorithm': 'QIIME (Pick closed-reference OTUs)',
            'pid': 5,
            'processed_date': '2012-10-02 17:30:00',
            'params': {
                'similarity': 0.97,
                'reference_name': 'Greengenes',
                'sortmerna_e_value': 1,
                'sortmerna_max_pos': 10000,
                'threads': 1,
                'sortmerna_coverage': 0.97,
                'reference_version': '13_8'},
            'samples': ['1.SKB1.640202', '1.SKB2.640194', '1.SKB3.640195',
                        '1.SKB4.640189', '1.SKB5.640181', '1.SKB6.640176',
                        '1.SKB7.640196', '1.SKB8.640193', '1.SKB9.640200',
                        '1.SKD1.640179', '1.SKD2.640178', '1.SKD3.640198',
                        '1.SKD4.640185', '1.SKD5.640186', '1.SKD6.640190',
                        '1.SKD7.640191', '1.SKD8.640184', '1.SKD9.640182',
                        '1.SKM1.640183', '1.SKM2.640199', '1.SKM3.640197',
                        '1.SKM4.640180', '1.SKM5.640177', '1.SKM6.640187',
                        '1.SKM7.640188', '1.SKM8.640201', '1.SKM9.640192']}, {
            'data_type': '16S',
            'algorithm': 'QIIME (Pick closed-reference OTUs)',
            'pid': 6,
            'processed_date': '2012-10-02 17:30:00',
            'params': {
                'similarity': 0.97,
                'reference_name': 'Silva',
                'sortmerna_e_value': 1,
                'sortmerna_max_pos': 10000,
                'threads': 1,
                'sortmerna_coverage': 0.97,
                'reference_version': 'test'},
            'samples': ['1.SKB1.640202', '1.SKB2.640194', '1.SKB3.640195',
                        '1.SKB4.640189', '1.SKB5.640181', '1.SKB6.640176',
                        '1.SKB7.640196', '1.SKB8.640193', '1.SKB9.640200',
                        '1.SKD1.640179', '1.SKD2.640178', '1.SKD3.640198',
                        '1.SKD4.640185', '1.SKD5.640186', '1.SKD6.640190',
                        '1.SKD7.640191', '1.SKD8.640184', '1.SKD9.640182',
                        '1.SKM1.640183', '1.SKM2.640199', '1.SKM3.640197',
                        '1.SKM4.640180', '1.SKM5.640177', '1.SKM6.640187',
                        '1.SKM7.640188', '1.SKM8.640201', '1.SKM9.640192']}, {
            'processed_date': '2012-10-02 17:30:00',
            'pid': 7,
            'samples': ['1.SKB1.640202', '1.SKB2.640194', '1.SKB3.640195',
                        '1.SKB4.640189', '1.SKB5.640181', '1.SKB6.640176',
                        '1.SKB7.640196', '1.SKB8.640193', '1.SKB9.640200',
                        '1.SKD1.640179', '1.SKD2.640178', '1.SKD3.640198',
                        '1.SKD4.640185', '1.SKD5.640186', '1.SKD6.640190',
                        '1.SKD7.640191', '1.SKD8.640184', '1.SKD9.640182',
                        '1.SKM1.640183', '1.SKM2.640199', '1.SKM3.640197',
                        '1.SKM4.640180', '1.SKM5.640177', '1.SKM6.640187',
                        '1.SKM7.640188', '1.SKM8.640201', '1.SKM9.640192'],
            'data_type': '16S'}])

        obs_info = qdb.util.generate_study_list([1, 2, 3, 4], True)
        self.assertEqual(obs_info, exp_info)


if __name__ == '__main__':
    main()
