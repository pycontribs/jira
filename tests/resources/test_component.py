from __future__ import annotations

from jira_svc.exceptions import jira_svcError
from tests.conftest import jira_svcTestCase, rndstr


class ComponentTests(jira_svcTestCase):
    def setUp(self):
        jira_svcTestCase.setUp(self)
        self.issue_1 = self.test_manager.project_b_issue1
        self.issue_2 = self.test_manager.project_b_issue2

    def test_2_create_component(self):
        proj = self.jira_svc.project(self.project_b)
        name = f"project-{proj}-component-{rndstr()}"
        component = self.jira_svc.create_component(
            name,
            proj,
            description="test!!",
            assigneeType="COMPONENT_LEAD",
            isAssigneeTypeValid=False,
        )
        self.assertEqual(component.name, name)
        self.assertEqual(component.description, "test!!")
        self.assertEqual(component.assigneeType, "COMPONENT_LEAD")
        self.assertFalse(component.isAssigneeTypeValid)
        component.delete()

    # Components field can't be modified from issue.update
    #    def test_component_count_related_issues(self):
    #        component = self.jira_svc.create_component('PROJECT_B_TEST',self.project_b, description='test!!',
    #                                               assigneeType='COMPONENT_LEAD', isAssigneeTypeValid=False)
    #        issue1 = self.jira_svc.issue(self.issue_1)
    #        issue2 = self.jira_svc.issue(self.issue_2)
    #        (issue1.update ({'components': ['PROJECT_B_TEST']}))
    #        (issue2.update (components = ['PROJECT_B_TEST']))
    #        issue_count = self.jira_svc.component_count_related_issues(component.id)
    #        self.assertEqual(issue_count, 2)
    #        component.delete()

    def test_3_update(self):
        try:
            components = self.jira_svc.project_components(self.project_b)
            for component in components:
                if component.name == "To be updated":
                    component.delete()
                    break
        except Exception:
            # We ignore errors as this code intends only to prepare for
            # component creation
            raise

        name = "component-" + rndstr()

        component = self.jira_svc.create_component(
            name,
            self.project_b,
            description="stand by!",
            leadUserName=self.jira_svc.current_user(),
        )
        name = "renamed-" + name
        component.update(
            name=name, description="It is done.", leadUserName=self.jira_svc.current_user()
        )
        self.assertEqual(component.name, name)
        self.assertEqual(component.description, "It is done.")
        self.assertEqual(component.lead.name, self.jira_svc.current_user())
        component.delete()

    def test_4_delete(self):
        component = self.jira_svc.create_component(
            "To be deleted", self.project_b, description="not long for this world"
        )
        myid = component.id
        component.delete()
        self.assertRaises(jira_svcError, self.jira_svc.component, myid)

    def test_delete_component_by_id(self):
        component = self.jira_svc.create_component(
            "To be deleted", self.project_b, description="not long for this world"
        )
        myid = component.id
        self.jira_svc.delete_component(myid)
        self.assertRaises(jira_svcError, self.jira_svc.component, myid)
