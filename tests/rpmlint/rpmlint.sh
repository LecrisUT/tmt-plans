#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
	rlPhaseStartSetup
		rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
		rlRun "pushd $tmp"
		rlRun "set -o pipefail"
		rlIsCentOS && rlLogWarning "rpmlint on CentOS+Epel is outdated. Reported information might not be relevant"
	rlPhaseEnd

	rlPhaseStartTest
		rlRun "rpm2cpio /var/share/test-artifacts/*.src.rpm | cpio -civ '*.spec'" 0 "Extract spec file from srpm"
		rlRun "cp ./*.spec $TMT_TEST_DATA/" 0 "Expose spec file"
		# The spec rpmlint is already executed from the srpm
		rlIsCentOS || rlRun "rpmlint -c $TMT_PLAN_DATA/packit.toml /var/share/test-artifacts/*.rpm" 0 "Run rpmlint (non-CentOS)"
		rlIsCentOS && rlRun "rpmlint /var/share/test-artifacts/*.rpm || true" 0 "Run rpmlint (CentOS)"
	rlPhaseEnd

	rlPhaseStartCleanup
		rlRun "popd"
		rlRun "rm -r $tmp" 0 "Remove tmp directory"
	rlPhaseEnd
rlJournalEnd
