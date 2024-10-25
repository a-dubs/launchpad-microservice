# Launchpad Microservice (lp-microservice) 

![Static Badge](https://img.shields.io/badge/version-v2.0.0-orange)

This microservice will run locally on your machine using snap daemon. Installing this is necessary for using my custom
[Launchpad Firefox Extension](https://github.com/a-dubs/lp-firefox-extension).

<br>

## Summary
 - This microservice is currently incredibly simple. It is a simple REST API that allows for posting and retrieving
   inline comments and review comments for Merge Proposals on Launchpad.
  - This microservice is intended to be used in conjunction with my custom [Launchpad Firefox Extension](
    https://github.com/a-dubs/lp-firefox-extension) to provide a more streamlined and user-friendly experience for
    reviewing Merge Proposals on Launchpad.

<br>

## Installation
1. Navigate to the [releases page](https://github.com/a-dubs/launchpad-microservice/releases) of this repository and
   download the latest snap package.
2. Navigate to the directory you download the snap package to and install the snap package using the following command:
   ```bash
   sudo snap install --classic --dangerous lp-microservice_2.0.0_amd64.snap
   ```
3. After installing, you need to authenticate the microservice with Launchpad. To do this, run the following command:
   ```bash
   lp-microservice.initialize
   ```
   This will open a browser window where you can authenticate the microservice with Launchpad. After authenticating,
   return to the terminal and press enter to complete the authentication process.
4. Voila! The microservice daemon is already running! 
5. If you want, you can verify that the microservice is running by running the following command:
   ```bash
   journalctl -f -u  snap.lp-microservice.lp-microservice.service
   ```
   If no errors are present, the microservice is running successfully.
6. If you haven't already, install my custom [Launchpad Firefox
   Extension](https://github.com/a-dubs/lp-firefox-extension) by following the instructions in the README of that
   repository.

<!-- 
## Image Gallery

### Placeholder Image (This is the image's caption/label)  
![Please end my suffering... (This is the image's alt text)](https://github.com/a-dubs/github-project-template/blob/master/image_gallery/Please_replace_me_I_am_begging_you.jpg)
<br>

## Project Metadata  

**Project Status** : (Active, Inactive, Archived)  
**Project Progress** : (Concept, In Progress, Functional, Complete)  
**Project dates** : Jan '00 - Present   -->

