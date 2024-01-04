# Documenting the Release Process

## Scope

The scope and purpose of these instructions are for maintainers who are looking to make
a release.

It forms a checklist of what needs to be done, together with sections for guidance.

- [ ] [Draft a New Release](#drafting-a-new-release)
- [ ] [Publishing the Release](#publishing-the-release)


## Drafting a New Release

1. Go to the https://github.com/pycontribs/jira/releases page and **"Draft a New Release"** using the button. Note: We currently use the 'Release Drafter' GHA that auto populates a draft release
2. Under the **"Choose a tag"**, make sure we follow the repository convention of a tag that IS NOT PREFIXED with a `v` e.g. `1.2.3` instead of `v1.2.3`
3. The tag **"Target"** should be `main`, the main branch.
3. The contents of the release should reference the PR reference and the individual who contributed. In some cases where maintainers take over a previous PR it is better practice to reference the name of the original submitter of the PR. e.g. The maintainer re-makes a PR based on a stale PR, the GHA would mention the maintainer by default as they created the PR, so the originator should be used.

## Publishing the Release

1. Pressing the **Edit** button of the latest draft release and pressing the **'Publish release'** button will trigger the release process.
2. The release process will request an approver from the list of release approvers. These are the maintainers specifically added here: https://github.com/pycontribs/jira/settings/environments/333132378/edit. This release environment also limits the branches that can be deployed. To follow the tag version convention mentioned earlier.
3. Finally this will automatically trigger the release CI action (as defined in our repository), this uses the relevant repository secrets to publish to PyPI.
