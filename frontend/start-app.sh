#!/usr/bin/env bash
#
#  Copyright 2023 DataRobot, Inc. and its affiliates.
#
#  All rights reserved.
#  This is proprietary source code of DataRobot, Inc. and its affiliates.
#  Released under the terms of DataRobot Tool and Utility Agreement.
#

echo "Starting App"
# streamlit run 'app.py' --server.maxUploadSize 200
streamlit run 'multistep_qa.py' --server.maxUploadSize 200