# qwebgisapp

Repository to extend QWC functionality on Linux based systems.

## Installation on client server

### Prerequisites for Debian/Ubuntu

Install base packages, also check apt.lst 

```
sudo apt-get install qgis-server postgis apache2 libapache2-mod-fcgid build-essential \
python-dev libpq-dev libffi-dev zip gdal-bin xvfb libsasl2-dev libldap2-dev libssl-dev
```

Install python-pip, also check pip.lst for python modules to install

```
curl https://bootstrap.pypa.io/get-pip.py | sudo python
```

### Configuration

Create application folder on client server and insert content from a template or an existing file and add APPID. 

```
[app]
name = appName
id = 96d59e24eda509604cdbc195df8c12a562016ac56d58d73c1801579623966fe1
```

You can use this command to create an id:

```
openssl rand -hex 32
```

Each application package gets an unified ID to make sure that there will be 
no duplicates and conflicts with other client packages.

```
sudo mkdir -p /var/client
cd /var/client
vim update.sh
```

execute script with

```
sudo bash update.sh
```

Next step is to copy content from a template or an existing config.ini 
file and adapt

```
vim config.ini
```

In [plugins] only make changes to active. required will be adapted automatically 
during setup.

```
[plugins]
active = xy, search_alkis, search_nominatim, fs_search, fs_details
```

Finally change owner to 

sudo chown -R www-data home/ log/ qwccache/ temp/

### Update

After system changes it is necessary to build a new package on the server first and then 
update the package on the client.

```
sudo bash update.sh
```

After minor changes in the config.ini it is only necessary to start a new setup.

```
sudo python $DIR/app/gbd/bin/setup.py $DIR/config.ini"
```

## Building the app on GBD development server

On the dev server, if not yet existing, create a directory for builds, e.g. 
`/var/gbd/builds`. Clone QWC and qwebgisapp in this dir:

```
cd /var/gbd/builds
git clone https://github.com/gbd-consult/QGIS-Web-Client
git clone https://github.com/gbd-consult/qwebgisapp
```

create an ini file and adapt APPID and other content if necessary. You can copy the content from an existing file:

```
cd /var/gbd/builds
cp client1.ini client2.ini
```

Next step is to run the build script:

```
python /var/gbd/builds/qwebgisapp/build.py path-to-config path-to-build dir

# Example for mabi
python /var/gbd/builds/qwebgisapp/build.py /var/gbd/builds/client1.ini /var/client/builds
```

This creates two files in the build dir:

- `<appID>.zip`
- `appName-update.sh`

### Installation

Upload `zip` and `update.sh` in a specific directory on the client. Go to this dir and run the `appName-update.sh`

```
sudo bash appName-update.sh
```

This creates the `/app` dir and the `config.ini`. Edit the config to reflect the local settings and run the setup script:

```
sudo python app/gbd/bin/setup.py config.ini
```

### Updates

Build the zip file as above, upload it to the client (replacing any existing zips) and re-run the "Installation" step.


## License

This program is free software. It is licensed under the the [MIT License](http://www.opensource.org/licenses/MIT).
