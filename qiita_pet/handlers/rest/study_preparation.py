# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

import os

import pandas as pd
from tornado.escape import json_encode, json_decode

from qiita_db.util import get_mountpoint
from qiita_db.artifact import Artifact
from qiita_pet.handlers.util import to_int
from qiita_db.exceptions import QiitaDBUnknownIDError, QiitaError
from qiita_db.metadata_template.prep_template import PrepTemplate
from qiita_db.handlers.oauth2 import authenticate_oauth
from .rest_handler import RESTHandler


class StudyPrepCreatorHandler(RESTHandler):
    # /api/v1/study/<int>/preparation/
    # TODO: do something smart about warnings, perhaps this should go in its
    # own endpoint i.e. /api/v1/study/<int>/preparation/validate

    @authenticate_oauth
    def post(self, study_id, *args, **kwargs):
        data_type = self.get_argument('data_type')
        investigation_type = self.get_argument('investigation_type', None)

        study_id = self.study_boilerplate(study_id)
        if study_id is None:
            return

        data = pd.DataFrame.from_dict(json_decode(self.request.body),
                                      orient='index')

        try:
            p = PrepTemplate.create(data, study_id, data_type,
                                    investigation_type)
        except QiitaError as e:
            self.write(json_encode({'message': e.message}))
            self.set_status(406)
            self.finish()
            return

        self.write({'id': p.id})
        self.set_status(201)
        self.finish()


class StudyPrepArtifactCreatorHandler(RESTHandler):
    # /api/v1/study/<int>/preparation/<int>/artifact
    @authenticate_oauth
    def post(self, study_id, prep_id):
        study = self.study_boilerplate(study_id)
        if study is None:
            return

        prep_id = to_int(prep_id)
        try:
            p = PrepTemplate(prep_id)
        except QiitaDBUnknownIDError:
            self.set_status(404)
            self.write({'message': 'Preparation not found'})
            self.finish()
            return

        if p.study_id != study.id:
            self.set_status(409)
            self.write({'message': 'Preparation ID not associated with the '
                                   'study'})
            self.finish()
            return

        artifact_deets = json_decode(self.request.body)
        _, upload = get_mountpoint('uploads')[0]
        base = os.path.join(upload, study_id)
        filepaths = [(os.path.join(base, fp), fp_type)
                     for fp, fp_type in artifact_deets['filepaths']]

        try:
            art = Artifact.create(filepaths,
                                  artifact_deets['artifact_type'],
                                  artifact_deets['artifact_name'],
                                  p)
        except QiitaError as e:
            self.write(json_encode({'message': e.message}))
            self.set_status(406)
            self.finish()
            return

        self.write({'id': art.id})
        self.set_status(201)
        self.finish()
