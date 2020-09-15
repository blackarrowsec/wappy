.PHONY: install, uptechs, install_requirements

install_requirements: uptechs
	python3 -m pip install -r requirements.txt

install: uptechs
	python3 setup.py install

uptechs:
	curl https://raw.githubusercontent.com/AliasIO/wappalyzer/master/src/technologies.json -s \
	-o wappy/technologies.json
