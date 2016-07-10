import re
import logging
import pytest
from six import integer_types

from tests import JiraTestManager
from tests import rndstr
from tests import find_by_key
from tests import find_by_key_value
from tests import not_on_custom_jira_instance
from jira import JIRAError


@pytest.fixture(scope='module')
def test_manager():
    return JiraTestManager()


@pytest.fixture()
def jira_admin(test_manager):
    return test_manager.jira_admin


@pytest.fixture()
def jira_normal(test_manager):
    return test_manager.jira_normal


@pytest.fixture(scope='module')
def td(test_manager):
    return {
        'project_b': test_manager.project_b,
        'project_a': test_manager.project_a,
        'issue_1': test_manager.project_b_issue1,
        'issue_2': test_manager.project_b_issue2,
        'issue_3': test_manager.project_b_issue3,
    }


def test_issue(test_manager, jira_admin, td):
    issue = jira_admin.issue(td['issue_1'])
    assert issue.key == td['issue_1']
    assert issue.fields.summary == 'issue 1 from %s' % td['project_b']


@pytest.mark.skipif(
    True,
    reason="disabled as it seems to be ignored by jira, returning all")
def test_issue_field_limiting(test_manager, jira_admin):
    issue = jira_admin.issue(td['issue_2'], fields='summary,comment')
    assert issue.fields.summary == 'issue 2 from %s' % td['project_b']
    comment1 = jira_admin.add_comment(issue, 'First comment')
    comment2 = jira_admin.add_comment(issue, 'Second comment')
    comment3 = jira_admin.add_comment(issue, 'Third comment')
    jira_admin.issue(td['issue_2'], fields='summary,comment')
    logging.warning(issue.raw['fields'])

    assert hasattr(issue.fields, 'reporter') is not True
    assert hasattr(issue.fields, 'progress') is not True

    comment1.delete()
    comment2.delete()
    comment3.delete()


def test_issue_equal(test_manager, jira_admin, td):
    issue1 = jira_admin.issue(td['issue_1'])
    issue2 = jira_admin.issue(td['issue_2'])
    issues = jira_admin.search_issues('key=%s' % td['issue_1'])

    assert issue1 == issues[0]
    assert issue2 != issues[0]


def test_issue_expandos(test_manager, jira_admin, td):
    issue = jira_admin.issue(td['issue_1'], expand='editmeta,schema')
    assert hasattr(issue, 'editmeta') is True
    assert hasattr(issue, 'schema') is True
    # testing for changelog is not reliable because
    # it may exist or not based on test order
    # self.assertFalse(hasattr(issue, 'changelog'))


@not_on_custom_jira_instance
def test_create_issue_with_fieldargs(test_manager, jira_admin, td):
    issue = jira_admin.create_issue(
        project=td['project_b'],
        summary='Test issue created',
        description='blahery',
        issuetype={'name': 'Bug'})  # customfield_10022='XSS'
    assert issue.fields.summary == 'Test issue created'
    assert issue.fields.description == 'blahery'
    assert issue.fields.issuetype.name == 'Bug'
    assert issue.fields.project.key == td['project_b']
    # self.assertEqual(issue.fields.customfield_10022, 'XSS')
    issue.delete()


@not_on_custom_jira_instance
def test_create_issue_with_fielddict(test_manager, jira_admin, td):
    fields = {
        'project': {
            'key': td['project_b']
        },
        'summary': 'Issue created from field dict',
        'description': "Some new issue for test",
        'issuetype': {
            'name': 'Bug'
        },
        # 'customfield_10022': 'XSS',
        'priority': {
            'name': 'Major'
        }
    }
    issue = jira_admin.create_issue(fields=fields)
    assert issue.fields.summary == 'Issue created from field dict'
    assert issue.fields.description == "Some new issue for test"
    assert issue.fields.issuetype.name == 'Bug'
    assert issue.fields.project.key == td['project_b']
    # self.assertEqual(issue.fields.customfield_10022, 'XSS')
    assert issue.fields.priority.name == 'Major'
    issue.delete()


@not_on_custom_jira_instance
def test_create_issue_without_prefetch(test_manager, jira_admin, td):
    issue = jira_admin.create_issue(
        prefetch=False,
        project=td['project_b'],
        summary='Test issue created',
        description='blahery',
        issuetype={'name': 'Bug'})  # customfield_10022='XSS'

    assert hasattr(issue, 'self')
    assert hasattr(issue, 'raw')
    assert 'fields' not in issue.raw
    issue.delete()


@not_on_custom_jira_instance
def test_update_with_fieldargs(test_manager, jira_admin, td):
    issue = jira_admin.create_issue(
        project=td['project_b'],
        summary='Test issue for updating',
        description='Will be updated shortly',
        issuetype={'name': 'Bug'})
    # customfield_10022='XSS')
    issue.update(
        summary='Updated summary',
        description='Now updated',
        issuetype={'name': 'Improvement'})
    assert issue.fields.summary == 'Updated summary'
    assert issue.fields.description == 'Now updated'
    assert issue.fields.issuetype.name == 'Improvement'
    # self.assertEqual(issue.fields.customfield_10022, 'XSS')
    assert issue.fields.project.key == td['project_b']
    issue.delete()


@not_on_custom_jira_instance
def test_update_with_fielddict(test_manager, jira_admin, td):
    issue = jira_admin.create_issue(
        project=td['project_b'],
        summary='Test issue for updating',
        description='Will be updated shortly',
        issuetype={'name': 'Bug'})
    fields = {
        'summary': 'Issue is updated',
        'description': "it sure is",
        'issuetype': {
            'name': 'Improvement'
        },
        # 'customfield_10022': 'DOC',
        'priority': {
            'name': 'Major'
        }
    }
    issue.update(fields=fields)

    assert issue.fields.summary == 'Issue is updated'
    assert issue.fields.description == 'it sure is'
    assert issue.fields.issuetype.name == 'Improvement'
    # self.assertEqual(issue.fields.customfield_10022, 'DOC')
    assert issue.fields.priority.name == 'Major'
    issue.delete()


def test_update_with_label(test_manager, jira_admin, td):
    issue = jira_admin.create_issue(
        project=td['project_b'],
        summary='Test issue for updating labels',
        description='Label testing',
        issuetype=test_manager.CI_JIRA_ISSUE)

    labelarray = ['testLabel']
    fields = {
        'labels': labelarray
    }

    issue.update(fields=fields)

    assert issue.fields.labels == ['testLabel']

    issue.delete()


def test_update_with_bad_label(test_manager, jira_admin, td):
    issue = jira_admin.create_issue(
        project=td['project_b'],
        summary='Test issue for updating labels',
        description='Label testing',
        issuetype=test_manager.CI_JIRA_ISSUE)

    issue.fields.labels.append('this should not work')

    fields = {
        'labels': issue.fields.labels
    }

    with pytest.raises(JIRAError):
        issue.update(fields=fields)

    issue.delete()


def test_delete(test_manager, jira_admin, td):
    issue = jira_admin.create_issue(
        project=td['project_b'],
        summary='Test issue created',
        description='Not long for this world',
        issuetype=test_manager.CI_JIRA_ISSUE)
    key = issue.key
    issue.delete()

    with pytest.raises(JIRAError):
        jira_admin.issue(key)


@not_on_custom_jira_instance
def test_createmeta(test_manager, jira_admin, td):
    meta = jira_admin.createmeta()
    ztravisdeb_proj = find_by_key(meta['projects'], td['project_b'])
    # we assume that this project should allow at least one issue type
    assert len(ztravisdeb_proj['issuetypes']) >= 1


@not_on_custom_jira_instance
def test_createmeta_filter_by_projectkey_and_name(test_manager, jira_admin, td):
    meta = jira_admin.createmeta(projectKeys=td['project_b'],
                                 issuetypeNames='Bug')
    assert len(meta['projects']) == 1
    assert len(meta['projects'][0]['issuetypes']) == 1


@not_on_custom_jira_instance
def test_createmeta_filter_by_projectkeys_and_name(test_manager, jira_admin, td):
    meta = jira_admin.createmeta(
        projectKeys=(td['project_a'], td['project_b']),
        issuetypeNames='Improvement')

    assert len(meta['projects']) == 2

    for project in meta['projects']:
        assert len(project['issuetypes']) == 1


@not_on_custom_jira_instance
def test_createmeta_filter_by_id(test_manager, jira_admin, td):
    projects = jira_admin.projects()
    proja = find_by_key_value(projects, td['project_a'])
    projb = find_by_key_value(projects, td['project_b'])
    meta = jira_admin.createmeta(
        projectIds=(proja.id, projb.id),
        issuetypeIds=('3', '4', '5'))

    assert len(meta['projects']) == 2

    for project in meta['projects']:
        assert len(project['issuetypes']) == 3


def test_createmeta_expando(test_manager, jira_admin, td):
    # limit to SCR project so the call returns promptly
    meta = jira_admin.createmeta(
        projectKeys=td['project_b'],
        expand='projects.issuetypes.fields')

    assert 'fields' in meta['projects'][0]['issuetypes'][0]


def test_assign_issue(test_manager, jira_admin, td):
    assert jira_admin.assign_issue(td['issue_1'], test_manager.CI_JIRA_ADMIN)
    assert jira_admin.issue(td['issue_1']).fields.assignee.name == \
        test_manager.CI_JIRA_ADMIN


def test_assign_issue_with_issue_obj(test_manager, jira_admin, td):
    issue = jira_admin.issue(td['issue_1'])
    x = jira_admin.assign_issue(issue, test_manager.CI_JIRA_ADMIN)

    assert x is True
    assert jira_admin.issue(td['issue_1']).fields.assignee.name == \
        test_manager.CI_JIRA_ADMIN


def test_assign_to_bad_issue_raises(test_manager, jira_admin):
    with pytest.raises(JIRAError):
        jira_admin.assign_issue('NOPE-1', 'notauser')


def test_comments(test_manager, jira_admin, td):
    for issue in [td['issue_1'], jira_admin.issue(td['issue_2'])]:
        jira_admin.issue(issue)
        comment1 = jira_admin.add_comment(issue, 'First comment')
        comment2 = jira_admin.add_comment(issue, 'Second comment')
        comments = jira_admin.comments(issue)
        assert comments[0].body == 'First comment'
        assert comments[1].body == 'Second comment'
        comment1.delete()
        comment2.delete()
        comments = jira_admin.comments(issue)
        assert len(comments) == 0


def test_add_comment(test_manager, jira_admin, td):
    comment = jira_admin.add_comment(
        td['issue_3'], 'a test comment!',
        visibility={'type': 'role', 'value': 'Administrators'})

    assert comment.body == 'a test comment!'
    assert comment.visibility.type == 'role'
    assert comment.visibility.value == 'Administrators'

    comment.delete()


def test_add_comment_with_issue_obj(test_manager, jira_admin, td):
    issue = jira_admin.issue(td['issue_3'])
    comment = jira_admin.add_comment(
        issue, 'a new test comment!',
        visibility={'type': 'role', 'value': 'Administrators'})

    assert comment.body == 'a new test comment!'
    assert comment.visibility.type == 'role'
    assert comment.visibility.value == 'Administrators'

    comment.delete()


def test_update_comment(test_manager, jira_admin, td):
    comment = jira_admin.add_comment(td['issue_3'], 'updating soon!')
    comment.update(body='updated!')

    assert comment.body == 'updated!'
    # self.assertEqual(comment.visibility.type, 'role')
    # self.assertEqual(comment.visibility.value, 'Administrators')

    comment.delete()


def test_editmeta(test_manager, jira_admin, td):
    for i in (td['issue_1'], td['issue_2']):
        meta = jira_admin.editmeta(i)
        assert 'assignee' in meta['fields']
        assert 'attachment' in meta['fields']
        assert 'comment' in meta['fields']
        assert 'components' in meta['fields']
        assert 'description' in meta['fields']
        assert 'duedate' in meta['fields']
        assert 'environment' in meta['fields']
        assert 'fixVersions' in meta['fields']
        assert 'issuelinks' in meta['fields']
        assert 'issuetype' in meta['fields']
        assert 'labels' in meta['fields']
        assert 'versions' in meta['fields']


def test_transitioning(test_manager, jira_admin, td):
    # we check with both issue-as-string or issue-as-object
    transitions = []
    for issue in [td['issue_2'], jira_admin.issue(td['issue_2'])]:
        transitions = jira_admin.transitions(issue)

        assert transitions
        assert 'id' in transitions[0]
        assert 'name' in transitions[0]

    assert transitions, "Expecting at least one transition"
    # we test getting a single transition
    transition = jira_admin.transitions(td['issue_2'],
                                        transitions[0]['id'])[0]
    assert transition == transitions[0]

    # we test the expand of fields
    transition = jira_admin.transitions(
        td['issue_2'],
        transitions[0]['id'],
        expand='transitions.fields')[0]
    assert 'fields' in transition

    # Testing of transition with field assignment is disabled now because
    # default workflows do not have it.

    # jira_admin.transition_issue(issue, transitions[0]['id'], assignee={'name': test_manager.CI_JIRA_ADMIN})
    # issue = jira_admin.issue(issue.key)
    # self.assertEqual(issue.fields.assignee.name, test_manager.CI_JIRA_ADMIN)
    #
    # fields = {
    #     'assignee': {
    #         'name': test_manager.CI_JIRA_USER
    #     }
    # }
    # transitions = jira_admin.transitions(issue.key)
    # self.assertTrue(transitions)  # any issue should have at least one transition available to it
    # transition_id = transitions[0]['id']
    #
    # jira_admin.transition_issue(issue.key, transition_id, fields=fields)
    # issue = jira_admin.issue(issue.key)
    # self.assertEqual(issue.fields.assignee.name, test_manager.CI_JIRA_USER)
    # self.assertEqual(issue.fields.status.id, transition_id)


def test_votes(test_manager, jira_admin, jira_normal, td):
    jira_normal.remove_vote(td['issue_1'])
    # not checking the result on this
    votes = jira_admin.votes(td['issue_1'])
    assert votes.votes == 0

    jira_normal.add_vote(td['issue_1'])
    new_votes = jira_admin.votes(td['issue_1'])
    assert votes.votes + 1 == new_votes.votes

    jira_normal.remove_vote(td['issue_1'])
    new_votes = jira_admin.votes(td['issue_1'])
    assert votes.votes == new_votes.votes


def test_votes_with_issue_obj(test_manager, jira_admin, jira_normal, td):
    issue = jira_normal.issue(td['issue_1'])
    jira_normal.remove_vote(issue)
    # not checking the result on this
    votes = jira_admin.votes(issue)
    assert votes.votes == 0

    jira_normal.add_vote(issue)
    new_votes = jira_admin.votes(issue)
    assert votes.votes + 1 == new_votes.votes

    jira_normal.remove_vote(issue)
    new_votes = jira_admin.votes(issue)
    assert votes.votes == new_votes.votes


def test_add_remove_watcher(test_manager, jira_admin, td):
    # removing it in case it exists, so we know its state
    jira_admin.remove_watcher(td['issue_1'], test_manager.CI_JIRA_USER)
    init_watchers = jira_admin.watchers(td['issue_1']).watchCount

    # adding a new watcher
    jira_admin.add_watcher(td['issue_1'], test_manager.CI_JIRA_USER)
    assert jira_admin.watchers(td['issue_1']).watchCount == init_watchers + 1

    # now we verify that remove does indeed remove watchers
    jira_admin.remove_watcher(td['issue_1'], test_manager.CI_JIRA_USER)
    new_watchers = jira_admin.watchers(td['issue_1']).watchCount
    assert init_watchers == new_watchers


@not_on_custom_jira_instance
def test_agile(test_manager, jira_admin, td):
    uniq = rndstr()
    board_name = 'board-' + uniq
    sprint_name = 'sprint-' + uniq

    b = jira_admin.create_board(board_name, td['project_a'])
    assert isinstance(b.id, integer_types)

    s = jira_admin.create_sprint(sprint_name, b.id)
    assert isinstance(s.id, integer_types)
    assert s.name == sprint_name
    assert s.state == 'FUTURE'

    jira_admin.add_issues_to_sprint(s.id, [td['issue_1']])

    sprint_field_name = "Sprint"
    sprint_field_id = [f['schema']['customId'] for f in jira_admin.fields()
                       if f['name'] == sprint_field_name][0]
    sprint_customfield = "customfield_" + str(sprint_field_id)

    updated_issue_1 = jira_admin.issue(td['issue_1'])
    serialised_sprint = getattr(updated_issue_1.fields, sprint_customfield)[0]

    # Too hard to serialise the sprint object.
    # Performing simple regex match instead.
    assert re.search('\[id=' + str(s.id) + ',', serialised_sprint)

    # jira_admin.add_issues_to_sprint(s.id, self.issue_2)

    # jira_admin.rank(self.issue_2, self.issue_1)

    s.delete()

    b.delete()
    # jira_admin.delete_board(b.id)


def test_worklogs(test_manager, jira_admin, td):
    worklog = jira_admin.add_worklog(td['issue_1'], '2h')
    worklogs = jira_admin.worklogs(td['issue_1'])

    assert len(worklogs) == 1
    worklog.delete()


def test_worklogs_with_issue_obj(test_manager, jira_admin, td):
    issue = jira_admin.issue(td['issue_1'])
    worklog = jira_admin.add_worklog(issue, '2h')
    worklogs = jira_admin.worklogs(issue)

    assert len(worklogs) == 1
    worklog.delete()


def test_worklog(test_manager, jira_admin, td):
    worklog = jira_admin.add_worklog(td['issue_1'], '1d 2h')
    new_worklog = jira_admin.worklog(td['issue_1'], str(worklog))

    assert new_worklog.author.name == test_manager.CI_JIRA_ADMIN
    assert new_worklog.timeSpent == '1d 2h'
    worklog.delete()


def test_worklog_with_issue_obj(test_manager, jira_admin, td):
    issue = jira_admin.issue(td['issue_1'])
    worklog = jira_admin.add_worklog(issue, '1d 2h')
    new_worklog = jira_admin.worklog(issue, str(worklog))

    assert new_worklog.author.name == test_manager.CI_JIRA_ADMIN
    assert new_worklog.timeSpent == '1d 2h'
    worklog.delete()


def test_add_worklog(test_manager, jira_admin, td):
    worklog_count = len(jira_admin.worklogs(td['issue_2']))
    worklog = jira_admin.add_worklog(td['issue_2'], '2h')

    assert worklog is not None
    assert len(jira_admin.worklogs(td['issue_2'])) == worklog_count + 1
    worklog.delete()


def test_add_worklog_with_issue_obj(test_manager, jira_admin, td):
    issue = jira_admin.issue(td['issue_2'])
    worklog_count = len(jira_admin.worklogs(issue))
    worklog = jira_admin.add_worklog(issue, '2h')

    assert worklog is not None
    assert len(jira_admin.worklogs(issue)) == worklog_count + 1
    worklog.delete()


def test_update_and_delete_worklog(test_manager, jira_admin, td):
    worklog = jira_admin.add_worklog(td['issue_3'], '3h')
    issue = jira_admin.issue(td['issue_3'], fields='worklog,timetracking')
    worklog.update(comment='Updated!', timeSpent='2h')

    assert worklog.comment == 'Updated!'
    # rem_estimate = issue.fields.timetracking.remainingEstimate
    assert worklog.timeSpent == '2h'

    issue = jira_admin.issue(td['issue_3'], fields='worklog,timetracking')

    assert issue.fields.timetracking.remainingEstimate == "1h"
    worklog.delete()

    issue = jira_admin.issue(td['issue_3'], fields='worklog,timetracking')
    assert issue.fields.timetracking.remainingEstimate == "3h"

# Nothing from remote link works
#    def test_remote_links(test_manager, jira_admin):
#        jira_admin.add_remote_link ('ZTRAVISDEB-3', globalId='python-test:story.of.horse.riding',
#        links = jira_admin.remote_links('QA-44')
#        self.assertEqual(len(links), 1)
#        links = jira_admin.remote_links('BULK-1')
#        self.assertEqual(len(links), 0)
#
#    @unittest.skip("temporary disabled")
#    def test_remote_links_with_issue_obj(test_manager, jira_admin):
#        issue = jira_admin.issue('QA-44')
#        links = jira_admin.remote_links(issue)
#        self.assertEqual(len(links), 1)
#        issue = jira_admin.issue('BULK-1')
#        links = jira_admin.remote_links(issue)
#        self.assertEqual(len(links), 0)
#
#    @unittest.skip("temporary disabled")
#    def test_remote_link(test_manager, jira_admin):
#        link = jira_admin.remote_link('QA-44', '10000')
#        self.assertEqual(link.id, 10000)
#        self.assertTrue(hasattr(link, 'globalId'))
#        self.assertTrue(hasattr(link, 'relationship'))
#
#    @unittest.skip("temporary disabled")
#    def test_remote_link_with_issue_obj(test_manager, jira_admin):
#        issue = jira_admin.issue('QA-44')
#        link = jira_admin.remote_link(issue, '10000')
#        self.assertEqual(link.id, 10000)
#        self.assertTrue(hasattr(link, 'globalId'))
#        self.assertTrue(hasattr(link, 'relationship'))
#
#    @unittest.skip("temporary disabled")
#    def test_add_remote_link(test_manager, jira_admin):
#        link = jira_admin.add_remote_link('BULK-3', globalId='python-test:story.of.horse.riding',
#                                         object={'url': 'http://google.com', 'title': 'googlicious!'},
#                                         application={'name': 'far too silly', 'type': 'sketch'}, relationship='mousebending')
# creation response doesn't include full remote link info, so we fetch it again using the new internal ID
#        link = jira_admin.remote_link('BULK-3', link.id)
#        self.assertEqual(link.application.name, 'far too silly')
#        self.assertEqual(link.application.type, 'sketch')
#        self.assertEqual(link.object.url, 'http://google.com')
#        self.assertEqual(link.object.title, 'googlicious!')
#        self.assertEqual(link.relationship, 'mousebending')
#        self.assertEqual(link.globalId, 'python-test:story.of.horse.riding')
#
#    @unittest.skip("temporary disabled")
#    def test_add_remote_link_with_issue_obj(test_manager, jira_admin):
#        issue = jira_admin.issue('BULK-3')
#        link = jira_admin.add_remote_link(issue, globalId='python-test:story.of.horse.riding',
#                                         object={'url': 'http://google.com', 'title': 'googlicious!'},
#                                         application={'name': 'far too silly', 'type': 'sketch'}, relationship='mousebending')
# creation response doesn't include full remote link info, so we fetch it again using the new internal ID
#        link = jira_admin.remote_link(issue, link.id)
#        self.assertEqual(link.application.name, 'far too silly')
#        self.assertEqual(link.application.type, 'sketch')
#        self.assertEqual(link.object.url, 'http://google.com')
#        self.assertEqual(link.object.title, 'googlicious!')
#        self.assertEqual(link.relationship, 'mousebending')
#        self.assertEqual(link.globalId, 'python-test:story.of.horse.riding')
#
#    @unittest.skip("temporary disabled")
#    def test_update_remote_link(test_manager, jira_admin):
#        link = jira_admin.add_remote_link('BULK-3', globalId='python-test:story.of.horse.riding',
#                                         object={'url': 'http://google.com', 'title': 'googlicious!'},
#                                         application={'name': 'far too silly', 'type': 'sketch'}, relationship='mousebending')
# creation response doesn't include full remote link info, so we fetch it again using the new internal ID
#        link = jira_admin.remote_link('BULK-3', link.id)
#        link.update(object={'url': 'http://yahoo.com', 'title': 'yahooery'}, globalId='python-test:updated.id',
#                    relationship='cheesing')
#        self.assertEqual(link.globalId, 'python-test:updated.id')
#        self.assertEqual(link.relationship, 'cheesing')
#        self.assertEqual(link.object.url, 'http://yahoo.com')
#        self.assertEqual(link.object.title, 'yahooery')
#        link.delete()
#
#    @unittest.skip("temporary disabled")
#    def test_delete_remove_link(test_manager, jira_admin):
#        link = jira_admin.add_remote_link('BULK-3', globalId='python-test:story.of.horse.riding',
#                                         object={'url': 'http://google.com', 'title': 'googlicious!'},
#                                         application={'name': 'far too silly', 'type': 'sketch'}, relationship='mousebending')
#        _id = link.id
#        link.delete()
#        self.assertRaises(JIRAError, jira_admin.remote_link, 'BULK-3', _id)
