
PYTHON ?= python
PREFIX ?= externaltools

all: patch config build install cp_emb

patch:
	./patch

clean-pyc:
	find $(PREFIX) -name "*.pyc" | xargs rm -f

clean:
	./waf distclean

config:
	./waf configure

build:
	./waf build

install:
	./waf install

cp_emb:
	cp  /afs/cern.ch/user/l/lhelary/public/TriggerEventNumberDimuons7TeV.root externaltools/EmbeddedCorrections/share/

uninstall:
	rm -rf $(PREFIX)

test:
	$(PYTHON) test.py

clean-src:
	rm -rf src

.PHONY: patch
