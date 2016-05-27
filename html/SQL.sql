
drop table setting;
create table setting (
	user_sid text,				--- ユーザを一意に示すID、MD5
	target_sid text,			--- ターゲットを一意に示すID、MD5
	friendly_name text,
----	target_number text,
	created timestamp,
	registered timestamp,
	lock int2
);

drop table calldata;
create table calldata (
	user_sid text,				--- ユーザを一意に示すID、MD5
	target_sid text,			--- ターゲットを一意に示すID、MD5
	voice_sid text,				--- 録音データを一意に示すID、MD5
	created timestamp,
	voice_text text,
---	call_from text,
	call_to text
);

---------
drop table usertable;
create table usertable (
	user_id text,
	user_sid text,			--- ユーザを一意に示すID、MD5
	email_addr text,
	passwd text,
	expires timestamp,
	last_login timestamp,
	lock int2,
	login_fail int2,		---　ログインの失敗回数
	last1pass text,
	last2pass text,
	last3pass text,
	force_pass_ch int2
);

insert into usertable (user_id,passwd,expires,last_login,lock,last1pass,last2pass,last3pass,force_pass_ch)
values ('admin','749f09bade8aca755660eeb17792da880218d4fbdc4e25fbec279d7fe9f65d70','1900-01-01 00:00','1900-01-01 00:00',0,'','','',1);

drop table sessiontable;
create table sessiontable (
    user_id text,
    sessionid text,
    expires timestamp
);

drop table errortable;
create table errortable (
    user_id_md5 text,
    attempt timestamp
);
