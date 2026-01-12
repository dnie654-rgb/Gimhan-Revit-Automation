# Gimhan Revit Automation

This repository contains a collection of pyRevit extensions for Autodesk Revit.

## Extensions

### 1. ParamTransfer
Transfers values from one parameter to another within selected elements.
- **Features**: Batch transfer, Type validation.

### 2. LinkTools
Tools for interacting with Revit Links.
- **Copy From Link**: Select and copy elements from a linked model into the current project, preserving location.

### 3. HostTools
Tools for modifying element hosts.
- **Change Level**: Batch change the Host Level of selected elements while preserving their 3D position (automatically adjusting offsets).

## Installation

### Option 1: Automatic Installation (Recommended)
1.  Download `Install_Gimhan_Extensions.bat` from this repository.
2.  Run the file.
3.  It will automatically download the extensions to your AppData folder and register them with pyRevit.

### Option 2: Manual Installation
1.  Clone or Download this repository.
2.  Open **pyRevit Settings**.
3.  Add the path to this folder in the **Custom Extension Directories** section.
4.  Reload pyRevit.

## Author
Gimhan Umendra
