#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成一份最小 .docx 培养方案，用来验证 docx 适配器（Word 原件这条路径）。"""
import sys

from docx import Document

doc = Document()
doc.add_heading('示例学院 数据科学试验班 本科人才培养方案', level=1)

p = doc.add_paragraph('专业类及专业类代码：数据科学试验班')
doc.add_paragraph('毕业学分要求')
doc.add_paragraph('总学分： 120，其中通识教育学分: 40。')
doc.add_paragraph('四 年制本科，实行弹性学习年限；授予学位门类： 理 学学士学位。')

doc.add_paragraph('通识教育： 40 学分')
doc.add_paragraph('思政类： 8 学分')
doc.add_paragraph('外语类： 8 学分')
rows = [
    ('10100001', 'Academic English（1）', '外语学院', '必修', '32', '2', '1秋'),
    ('10100002', 'Academic English（2）', '外语学院', '必修', '32', '2', '1春'),
]
t = doc.add_table(rows=1, cols=7)
t.style = 'Table Grid'
hdr = t.rows[0].cells
for i, h in enumerate(['课程编号', '课程名称', '开课单位', '类别', '学时', '学分', '修读学期']):
    hdr[i].text = h
for r in rows:
    cells = t.add_row().cells
    for i, v in enumerate(r):
        cells[i].text = v

doc.add_paragraph('大类平台教育： 80 学分')
doc.add_paragraph('学院平台课： 12 学分')
t2 = doc.add_table(rows=1, cols=7)
t2.style = 'Table Grid'
for i, h in enumerate(['课程编号', '课程名称', '开课单位', '类别', '学时', '学分', '修读学期']):
    t2.rows[0].cells[i].text = h
rows2 = [
    ('20200001', '高等数学', '数学学院', '必修', '80', '5', '1秋'),
    ('20200002', '线性代数', '数学学院', '必修', '48', '3', '1春'),
    ('20200003', '概率论', '数学学院', '必修', '48', '3', '2秋'),
]
for r in rows2:
    cells = t2.add_row().cells
    for i, v in enumerate(r):
        cells[i].text = v

doc.save(sys.argv[1])
print('wrote', sys.argv[1])
