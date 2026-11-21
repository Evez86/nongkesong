import React, { useLayoutEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { campusLoginUrl, campusPortal, campusSchool } from './campusApi.js';
import { CampusSyncStatus } from './CampusSyncStatus.jsx';
import './campus.css';

export function CampusCatButton({ compact = false, connected, onOpen, scene }) {
  return (
    <button className={compact ? 'campus-cat-chip' : 'campus-cat-hotspot'} type="button"
      aria-haspopup="dialog" aria-label="点击橘猫，打开校园登录" onClick={onOpen}>
      {compact && <>
        <span className="campus-cat-chip__picture" style={{ backgroundImage: `url(${scene})` }} aria-hidden="true" />
        {connected ? '校园已连接' : '校园登录'}
      </>}
    </button>
  );
}

export function CampusDialog({ campus, onClose }) {
  const dialog = useRef(null);
  const { phase, session, dataPhase, academic, refresh, logout } = campus;

  useLayoutEffect(() => {
    dialog.current.showModal();
  }, []);

  const connected = phase === 'connected' || phase === 'loggingOut';
  const demo = session?.demo || academic?.source === 'demo';
  const canRetry = ['error', 'denied', 'idle'].includes(dataPhase);

  return (
    <dialog className="campus-dialog" ref={dialog} onClose={onClose} aria-labelledby="campus-title">
      <header>
        <h2 id="campus-title">校园登录</h2>
        <button className="campus-dialog__close" type="button" aria-label="关闭校园登录" autoFocus
          onClick={() => dialog.current.close()}><X size={20} aria-hidden="true" /></button>
      </header>
      <div className="campus-dialog__body">
        <p className="campus-dialog__school">{campusSchool} · 综合服务平台</p>
        {connected ? (
          <>
            {phase === 'connected' && <p role="status">{demo ? '校园联调 · 测试账号' : '校园账号已连接'}{session?.name && ` · ${session.name}`}</p>}
            <CampusSyncStatus campus={campus} />
            <footer>
              <button type="button" className="campus-button" disabled={phase === 'loggingOut'} onClick={logout}>
                {phase === 'loggingOut' ? '正在退出…' : '退出松果来信'}
              </button>
              {canRetry && phase === 'connected' && (
                <button type="button" className="campus-button" onClick={refresh}>重新同步</button>
              )}
              {academic && <a className="campus-button campus-button--primary" href="#/notebook/courses">查看学期课程簿</a>}
            </footer>
          </>
        ) : (
          <>
            <p>学号和密码在学校统一身份认证页面填写。</p>
            <CampusSyncStatus campus={campus} />
            {phase === 'preview' && <p className="campus-dialog__note">当前可在学校官网登录。松果来信的数据同步待校方授权接入。</p>}
            <footer>
              {phase === 'signedOut' ? (
                <a className="campus-button campus-button--primary" href={campusLoginUrl}>使用中农大账号登录</a>
              ) : phase !== 'checking' && (
                <a className="campus-button campus-button--primary" href={campusPortal} target="_blank"
                  rel="noopener noreferrer">前往综合服务平台<span className="campus-sr-only">（在新标签页打开）</span></a>
              )}
              {phase === 'error' && <button className="campus-button" type="button" onClick={refresh}>重新检查</button>}
              {phase === 'preview' && <a className="campus-button" href="#/notebook">先看看手帐</a>}
            </footer>
          </>
        )}
      </div>
    </dialog>
  );
}
