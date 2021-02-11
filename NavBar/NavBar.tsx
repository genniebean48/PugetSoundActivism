import ReactDOM from 'react-dom';
import React from 'react';
import './less';
import './navBar.less';

    const NavBar = (
            <div className="NavBar">
                <ul>
                    {/*// <li><img src="puget_icon.gif" alt="picture"/></li>*/}
                    <li id="title"> UPS ACTivism Hub</li>
                    <li><a> Home </a></li>
                    <li><a> Club Info </a></li>
                    <li><a> Resources </a></li>
                    <li><a id="login"> Login </a></li>
                </ul>
            </div>
    )

ReactDOM.render(NavBar, document.getElementById('root'));