.PHONY: install, uptechs, install_requirements

reqs_and_uptade: install_requirements uptechs

install_requirements:
	python3 -m pip install -r requirements.txt

install:
	python3 setup.py install
	wappy-update

uptechs:
	python3 wappy-update.py
