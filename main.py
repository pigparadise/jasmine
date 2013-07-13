# -*- coding:utf-8 -*-
import os
import logging
import shutil
import copy
import json

import markdown
import jinja2 as jinja
from datetime import datetime

import config

jinja_env = None
def init_jinja_env(*dirs):
    global jinja_env
    jinja_env = jinja.Environment(loader=jinja.FileSystemLoader(dirs))


g_rdata = {}
def init_global_render_params(infos):
    global g_rdata
    g_rdata = {
        "site": config.site,
        "disqus": config.disqus,
        "tags": parse_tags(infos),
        "archives": parse_archives(infos),
    }

def get_global_render_params():
    global g_rdata
    return g_rdata


def write_file(fpath, data):
    dir_path = os.path.dirname(fpath)
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)
    open(fpath, "wb").write(data)


def collect_blog_infos(input_dir):
    result = []
    for dirpath, dirnames, filenames in os.walk(input_dir):
        rel_dirpath = 'blog/' + dirpath[len(input_dir):].strip(os.sep)
        posts = []
        mds = set([])
        jinjas = set([])

        # find all files
        for fname in filenames:
            name, ext = os.path.splitext(fname)
            if ext == '.post':
                posts.append(name)
            elif ext == '.md':
                mds.add(name)
            elif ext == '.jinja':
                jinjas.add(name)

        # find every post
        for name in posts:
            post_fpath = os.path.join(dirpath, name+".post")
            try:
                data = json.load(open(post_fpath))
            except:
                logging.warning("post %s need a json file" % post_fpath)
                continue

            _id = str(data.get('id', '')).strip()
            title = data.get('title', '').strip()
            if not title:
                logging.warning("post %s don't has title" % post_fpath)
                continue

            tags = data.get('tags', [])
            if type(tags) != list:
                logging.warning("post %s tags need a list" % post_fpath)
                continue

            try:
                date = datetime.strptime(data['date'], '%Y-%m-%d %H:%M')
            except:
                logging.warning("post %s date should like 2013-5-5 18:12" % post_fpath)
                continue
            
            if name in jinjas: # jinja > mds
                content = os.path.join(dirpath, name+".jinja")
            elif name in mds:
                content = os.path.join(dirpath, name+".md")
            else:
                logging.warning("post %s don't has content template" % post_fpath)
                continue

            info = {
                "id": _id,
                "title": title,
                "tags": tags,
                "date": date,
                "content": content,
                "name": name,

                "dir": rel_dirpath,
                "path": os.path.join(rel_dirpath, name + ".html")
            }
            result.append(info)

    result.sort(key=lambda item: item['date'], reverse=True)
    return result


def render_jinja(template, data={}):
    params = get_global_render_params()
    params.update(data)
    return jinja_env.get_template(template).render(params).encode('utf-8')

    
def render_content(fpath):
    name, ext = os.path.splitext(fpath)
    s = open(fpath).read().decode('utf-8')
    if ext == '.md':
        return markdown.markdown(s, output_format='html5')

    if ext == '.jinja':
        return jinja_env.from_string(s).render()
    return ''


def create_blogs(posts, output_dir):
    # sort infos
    post_num = len(posts)
    for idx, post in enumerate(posts):
        # print post
        content = render_content(post["content"])
        post["content"] = content
        
        # prev and next
        if idx == 0:
            prev_post = None
        else:
            prev_post = posts[idx - 1]

        if idx == (post_num - 1):
            next_post = None
        else:
            next_post = posts[idx + 1]

        params = {
            "title": post["title"],
            "post": post,
            "prev_post": prev_post,
            "next_post": next_post
        }
        fdata = render_jinja("post.jinja", params)
        fpath = os.path.join(output_dir, post["path"])
        write_file(fpath, fdata)


def parse_tags(infos):
    tags = {}
    for info in infos:
        for tag in info["tags"]:
            if tag not in tags:
                tags[tag] = []
            tags[tag].append({
                "title": info['title'],
                "path": info['path'],
                "date": info['date']
            })
    return tags


def create_tags(infos, output_dir):
    for tag, posts in parse_tags(infos).iteritems():
        params = {
            "tag": tag,
            "posts": posts
        }
        fdata = render_jinja("tag.jinja", params)
        fpath = os.path.join(output_dir, "tags/%s.html" % tag)
        write_file(fpath, fdata)


def parse_archives(infos):
    archives = {}
    for info in infos:
        date = info['date']
        key = datetime(date.year, date.month, 1)
        if key not in archives:
            archives[key] = []
        archives[key].append({
            "title": info['title'],
            "path": info['path'],
            "date": info['date']
        })
    return archives


def create_archives(infos, output_dir):
    for key, posts in parse_archives(infos).iteritems():
        params = {
            "date": key,
            "posts": posts
        }
        fdata = render_jinja("archive.jinja", params)
        name = key.strftime('%Y_%m')
        fpath = os.path.join(output_dir, "archives/%s.html" % name)
        write_file(fpath, fdata)


def create_index(infos, output_dir):
    r_data = {
        "title": config.site['name'],
        "posts": infos
    }
    fdata = render_jinja("index.jinja", r_data)
    fpath = os.path.join(output_dir, "index.html")
    write_file(fpath, fdata)


def create_about(output_dir):
    fdata = render_jinja("about.jinja")
    fpath = os.path.join(output_dir, "about.html")
    write_file(fpath, fdata)


def copy_static(input_dir, output_dir):
    for name in ["css", "js", "img"]:
        _dir = os.path.join(input_dir, name)
        if not os.path.isdir(_dir):
            continue
        shutil.copytree(_dir, os.path.join(output_dir, name))


def main(input_dir, output_dir):
    # init dest_dir
    shutil.rmtree(output_dir, ignore_errors=True)
    os.mkdir(output_dir)
    init_jinja_env(os.path.join(input_dir, 'template'))
    infos = collect_blog_infos(os.path.join(input_dir, 'blog'))
    init_global_render_params(infos)
    create_blogs(infos, output_dir)
    create_tags(infos, output_dir)
    create_archives(infos, output_dir)
    create_about(output_dir)
    create_index(infos, output_dir)
    copy_static(input_dir, output_dir)


import optparse
def get_optparse():
    parser = optparse.OptionParser()
    parser.add_option('-i', '--input', dest = 'input', default='./input',
                      help = 'input dir', metavar='INPUT')
    parser.add_option('-o', '--output', dest ='output', default="./output",
                      help = 'output file', metavar='OUTPUT')
    return parser

if __name__ == '__main__':
    opt, args = get_optparse().parse_args()
    main(opt.input, opt.output)

