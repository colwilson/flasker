#!/usr/bin/env python

from flask import render_template
from flasker import current_project

app = current_project.app

@app.route('/')
def index():
  return render_template('index.html')

