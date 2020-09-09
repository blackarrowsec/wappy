.PHONY: install, uptechs


install: uptechs
	python3 -m pip install -r requirements.txt

uptechs:
	curl https://raw.githubusercontent.com/AliasIO/wappalyzer/master/src/technologies.json -Os
