#!/usr/bin/env python
import os
import unittest
import sys
from mock import patch, Mock
from StringIO import StringIO

import repoguard
from codechecker import CodeCheckerFactory

APPDIR = "%s/" % os.path.dirname(os.path.realpath(__file__))


class LocalRepoTestCase(unittest.TestCase):
    def setUp(self):
        self.ra = repoguard.createInitializedRepoguardInstance()
        # patch test repo list
        self.ra.REPO_LIST_PATH = APPDIR+'test_data/test_repo_list.json'
        self.ra.REPO_STATUS_PATH = APPDIR+'test_data/test_repo_status.json'
        self.ra.loadRepoListFromFile()
        self.ra.readRepoStatusFromFile()
        self.ra.resetRepoLimits()

    def mock_os_listdir(self):
        return ['aaaaa', 'bbbbb', 'ccccc']

    def test_search_repo_dir(self):
        dirlist = ['test_1234', 'test2_123', 'test_test', '0test_123', '.test_123456', 'test', 'test_other_12345', '12345']
        self.assertEqual(self.ra.searchRepoDir(dirlist, 'test', '1234'), 'test_1234')
        self.assertFalse(self.ra.searchRepoDir(dirlist, 'test2', '1234'))
        self.assertFalse(self.ra.searchRepoDir(dirlist, 'test', '12345'))
        self.assertFalse(self.ra.searchRepoDir(dirlist, 'test', '123456'))
        self.assertFalse(self.ra.searchRepoDir(dirlist, '', '12345'))
        self.assertEqual(self.ra.searchRepoDir(dirlist, 'test_other', '12345'), 'test_other_12345')

    @patch('os.path.isfile', return_value=False)
    def test_detect_paths_dev(self, *mocks):
        self.ra.detectPaths()
        self.assertFalse(self.ra.RUNNING_ON_PROD)

    @patch('os.path.isfile', return_value=True)
    def test_detect_paths_prod(self, *mocks):
        self.ra.detectPaths()
        self.assertTrue(self.ra.RUNNING_ON_PROD)

    @patch('subprocess.check_output', return_value='1163bec4351413be354f7c88317647815b000000\nAAAAbec4351413be354f7c88317647815b009999\n')
    def test_get_last_commit_hashes(self, *mocks):
        retVal = self.ra.getLastCommitHashes('123123', 'reponameABCD')
        self.assertEqual(mocks[0].call_args_list[0][0], (['git', 'rev-list', '--remotes', '--max-count=100'],))
        self.assertEqual(retVal, ['1163bec4351413be354f7c88317647815b000000', 'AAAAbec4351413be354f7c88317647815b009999'])

    def test_should_skip_due_language(self):
        rd = {}
        rd["name"] = "to_skip"
        rd["language"] = "python"
        self.ra.resetRepoLimits()
        self.ra.setRepoLanguageLimitation(["notpython"])
        self.assertTrue(self.ra.shouldSkip(rd))

    def test_should_skip_due_language_false(self):
        rd = {}
        rd["name"] = "to_skip"
        rd["language"] = "python"
        self.ra.resetRepoLimits()
        self.ra.setRepoLanguageLimitation(["python"])
        self.assertFalse(self.ra.shouldSkip(rd))

    def test_should_skip_due_name(self):
        rd = {}
        rd["name"] = "reponame"
        rd["language"] = "python"
        self.ra.resetRepoLimits()
        self.ra.setSkipRepoList(['a', 'reponame', 'b'])
        self.assertTrue(self.ra.shouldSkip(rd))

    def test_should_skip_due_name_false(self):
        rd = {}
        rd["name"] = "reponame"
        rd["language"] = "python"
        self.ra.resetRepoLimits()
        self.ra.setSkipRepoList(['notreponame'])
        self.assertFalse(self.ra.shouldSkip(rd))

    def test_get_new_hashes(self):
        self.ra.repoStatusNew["8742897"]["last_checked_hashes"] = ["d", "c", "b", "a"]
        self.ra.repoStatus["8742897"]["last_checked_hashes"] = ["b", "a"]
        ret_arr = self.ra.getNewHashes("8742897")
        self.assertEqual(ret_arr, ["d", "c"])

    @patch('repoguard.RepoGuard.shouldSkip', return_value=False)
    @patch('os.listdir', return_value=[])
    @patch('subprocess.check_output')
    @patch('repoguard.RepoGuard.updateRepoStatusById')
    def test_update_local_repos_no_prev_dirs(self, *mocks):
        self.ra.updateLocalRepos()
        # check if git clone is called as required everywhere
        self.assertEqual(mocks[1].call_args_list[0][0], ([u'git', u'clone', u'git@github.com:prezi/object-library-service.git', u'%s/object-library-service_6125572' % self.ra.WORKING_DIR],))
        self.assertEqual(mocks[1].call_args_list[1][0], ([u'git', u'clone', u'git@github.com:prezi/project-startup.git', u'%s/project-startup_7092651' % self.ra.WORKING_DIR],))
        self.assertEqual(mocks[1].call_args_list[2][0], ([u'git', u'clone', u'git@github.com:prezi/data-research.git', u'%s/data-research_7271766' % self.ra.WORKING_DIR],))
        self.assertEqual(self.ra.repoStatus['6125572']['last_checked_hashes'], [])
        self.assertEqual(self.ra.repoStatus['7092651']['last_checked_hashes'], [])
        self.assertEqual(self.ra.repoStatus['7271766']['last_checked_hashes'], [])
        self.assertEqual(len(mocks[1].call_args_list), 3)

    @patch('os.listdir', return_value=[])
    @patch('subprocess.check_output')
    @patch('repoguard.RepoGuard.updateRepoStatusById')
    def test_update_local_repos_no_prev_dirs_skip_repo(self, *mocks):
        self.ra.setSkipRepoList(('project-startup'))
        self.ra.updateLocalRepos()
        # check if git clone is called as required everywhere
        self.assertEqual(mocks[1].call_args_list[0][0], ([u'git', u'clone', u'git@github.com:prezi/object-library-service.git', u'%s/object-library-service_6125572' % self.ra.WORKING_DIR],))
        self.assertEqual(mocks[1].call_args_list[1][0], ([u'git', u'clone', u'git@github.com:prezi/data-research.git', u'%s/data-research_7271766' % self.ra.WORKING_DIR],))
        self.assertEqual(self.ra.repoStatus['6125572']['last_checked_hashes'], [])
        self.assertEqual(self.ra.repoStatus['7271766']['last_checked_hashes'], [])
        self.assertEqual(len(mocks[1].call_args_list), 2)

    @patch('os.listdir', return_value=[])
    @patch('subprocess.check_output')
    @patch('repoguard.RepoGuard.updateRepoStatusById')
    def test_update_local_repos_no_prev_dirs_limit_language(self, *mocks):
        self.ra.setRepoLanguageLimitation(('python'))
        self.ra.updateLocalRepos()
        # check if git clone is called as required everywhere
        self.assertEqual(mocks[1].call_args_list[0][0], ([u'git', u'clone', u'git@github.com:prezi/object-library-service.git', u'%s/object-library-service_6125572' % self.ra.WORKING_DIR],))
        self.assertEqual(mocks[1].call_args_list[1][0], ([u'git', u'clone', u'git@github.com:prezi/project-startup.git', u'%s/project-startup_7092651' % self.ra.WORKING_DIR],))
        self.assertEqual(self.ra.repoStatus['6125572']['last_checked_hashes'], [])
        self.assertEqual(self.ra.repoStatus['7092651']['last_checked_hashes'], [])
        self.assertEqual(len(mocks[1].call_args_list), 2)

    @patch('repoguard.RepoGuard.shouldSkip', return_value=False)
    @patch('os.listdir', return_value=['project-startup_7092651'])
    @patch('subprocess.check_output')
    @patch('repoguard.RepoGuard.updateRepoStatusById')
    def test_update_local_repos_both_clone_and_pull(self, *mocks):
        self.ra.updateLocalRepos()
        # check if git clones and pulls are called as required everywhere
        self.assertEqual(mocks[1].call_args_list[0][0], ([u'git', u'clone', u'git@github.com:prezi/object-library-service.git', u'%s/object-library-service_6125572' % self.ra.WORKING_DIR],))
        self.assertEqual(mocks[1].call_args_list[1][0], ([u'git', u'pull'],))
        self.assertEqual(mocks[1].call_args_list[1][1], {'cwd': '%s/project-startup_7092651/' % self.ra.WORKING_DIR})
        self.assertEqual(mocks[1].call_args_list[2][0], ([u'git', u'clone', u'git@github.com:prezi/data-research.git', u'%s/data-research_7271766' % self.ra.WORKING_DIR],))
        self.assertEqual(self.ra.repoStatus['6125572']['last_checked_hashes'], [])
        self.assertEqual(self.ra.repoStatus['7271766']['last_checked_hashes'], [])
        self.assertEqual(len(mocks[1].call_args_list), 3)

    @patch('repoguard.RepoGuard.shouldSkip', return_value=False)
    @patch('os.listdir', return_value=['project-startup_7092651', 'object-library-service_6125572', 'data-research_7271766'])
    @patch('subprocess.check_output')
    @patch('repoguard.RepoGuard.updateRepoStatusById')
    def test_update_local_repos_only_pulls(self, *mocks):
        self.ra.updateLocalRepos()
        # check if git pull is called as required everywhere
        self.assertEqual(mocks[1].call_args_list[0][0], ([u'git', u'pull'],))
        self.assertEqual(mocks[1].call_args_list[0][1], {'cwd': '%s/object-library-service_6125572/' % self.ra.WORKING_DIR})
        self.assertEqual(mocks[1].call_args_list[1][0], ([u'git', u'pull'],))
        self.assertEqual(mocks[1].call_args_list[1][1], {'cwd': '%s/project-startup_7092651/' % self.ra.WORKING_DIR})
        self.assertEqual(mocks[1].call_args_list[2][0], ([u'git', u'pull'],))
        self.assertEqual(mocks[1].call_args_list[2][1], {'cwd': '%s/data-research_7271766/' % self.ra.WORKING_DIR})


class CheckNewCodeTest(unittest.TestCase):
    def setUp(self):
        rules = {
            "test::file_modified": {
                "diff": "del",
                "line": [{"match": "^-- a/zuisite/my/views\\.py"}]
            },
            "test::function_modified": {
                "line": [{"match": "def settings_and_license"}],
                "description": "settings_and_license function modified"
            },
            "test::string_matches": {
                "diff": "add",
                "line": [{"match": "datetime\\.date\\.today\\(\\).*"}],
                "description": "datetime.date.today() called"
            }
        }
        self.ra = repoguard.createInitializedRepoguardInstance()
        self.ra.code_checker = CodeCheckerFactory(rules).create()
        self.ra.REPO_LIST_PATH = APPDIR+'test_data/test_repo_list.json'
        self.ra.loadRepoListFromFile()
        self.ra.REPO_STATUS_PATH = APPDIR+'test_data/test_repo_status.json'
        self.ra.readRepoStatusFromFile()
        self.ra.resetRepoLimits()
        self.output = StringIO()
        self.saved_stdout = sys.stdout
        sys.stdout = self.output

    def tearDown(self):
        self.output.close()
        sys.stdout = self.saved_stdout

    @patch('os.listdir', return_value=['aaaa-test', 'bbbb_test', '.444444_test3'])
    @patch('os.path.isdir', return_value=True)
    @patch('subprocess.check_output')
    def test_no_repo_dirs(self, *mocks):
        self.ra.checkNewCode()
        self.assertEqual(self.output.getvalue(), "skip aaaa-test (not repo directory)\nskip bbbb_test (not repo directory)\nskip .444444_test3 (not repo directory)\n")

    @patch('os.listdir', return_value=['newrepo_123456'])
    @patch('os.path.isdir', return_value=True)
    @patch('subprocess.check_output')
    def test_insert_new_repo(self, *mocks):
        self.ra.checkNewCode()
        self.assertIn('123456', self.ra.repoStatus)
        self.assertEqual(self.ra.repoStatus['123456']['last_checked_hashes'], [])

    @patch('subprocess.check_output')
    def test_check_by_rev_hash(self, *mocks):
        mocks[0].return_value = open(APPDIR+'test_data/test_git_show.txt', 'r').read()
        res = self.ra.checkByRevHash('de74d131fbcca4bacac02523ef8d45c1dc8e2bde', 'testdir', '123123')
        expected_res = [
            (	u'test::file_modified',
                '/zuisite/my/views.py',
                'de74d131fbcca4bacac02523ef8d45c1dc8e2bde', '--- a/zuisite/my/views.py', 'testdir', '123123'),
            (	u'test::function_modified',
                '/zuisite/my/views.py',
                'de74d131fbcca4bacac02523ef8d45c1dc8e2bde',
                ' def settings_and_license(request, tab=None, group_id=None, grouplicense=False):', 'testdir', '123123'),
            (	u'test::string_matches',
                '/zuisite/my/views.py',
                'de74d131fbcca4bacac02523ef8d45c1dc8e2bde',
                '+                    "expired": True if group_license_expiry < datetime.date.today() else False,', 'testdir', '123123')
        ]
        self.assertEqual(res, expected_res)

    @patch('subprocess.check_output', return_value='1163bec4351413be354f7c88317647815b000000\n')
    @patch('repoguard.RepoGuard.getNewHashes', return_value=['1163bec4351413be354f7c88317647815b000000'])
    @patch('repoguard.RepoGuard.checkByRevHash', return_value=['test_alert', 'test_path/test_file.py', '1163bec4351413be354f7c88317647815b000000', 'matching line ...'])
    def test_check_by_repo_id_with_new_hashes(self, *mocks):
        tres = self.ra.checkByRepoId('8742897', 'zuisite')
        self.assertEqual(tres, ['test_alert', 'test_path/test_file.py', '1163bec4351413be354f7c88317647815b000000', 'matching line ...'])

    @patch('subprocess.check_output', return_value='1163bec4351413be354f7c88317647815b000000\n')
    @patch('repoguard.RepoGuard.getNewHashes', return_value=[])
    @patch('repoguard.RepoGuard.checkByRevHash', return_value=['test_alert', 'test_path/test_file.py', '1163bec4351413be354f7c88317647815b000000', 'matching line ...'])
    def test_check_by_repo_id_without_new_hashes(self, *mocks):
        tres = self.ra.checkByRepoId('8742897', 'zuisite')
        self.assertEqual(tres, [])


class AlertSubscriptionTestCase(unittest.TestCase):
    def setUp(self):
        self.repoguard = repoguard.createInitializedRepoguardInstance()
        self.repoguard.subscribers = {"xxe::simple": ["A", "B", "C"], "xxe::*": ["A", "D"]}

    def test_simple_match(self):
        users = self.repoguard.find_subscribed_users("xxe::simple")
        self.assertIn("A", users)
        self.assertIn("B", users)
        self.assertIn("C", users)
        self.assertIn("D", users)

    def test_limit_match(self):
        users = self.repoguard.find_subscribed_users("xxe::simplealert")
        self.assertIn("A", users)
        self.assertNotIn("B", users)
        self.assertNotIn("C", users)
        self.assertIn("D", users)

    @patch('notifier.EmailNotifier.create_notification')
    def test_send_alerts(self, *mocks):
        self.repoguard.checkResults = [
            ("xxe::test", "file", "1231commit", "line1", "repo"),
            ("xxe::simple", "file", "1231commit", "line1", "repo"),
            ("test::test", "file", "1231commit", "line1", "repo")
        ]
        mock_notification = Mock()
        mocks[0].return_value = mock_notification

        self.repoguard.sendResults()

        self.assertEqual(4, mocks[0].call_count)


def main():
    unittest.main()

if __name__ == '__main__':
    main()