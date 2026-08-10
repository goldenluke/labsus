// src/components/Layout.jsx
import React from 'react';
import NavBar from './NavBar';

const Layout = ({ children }) => {
    return (
        <div>
        <NavBar />
        <main>{children}</main>
        </div>
    );
};
export default Layout;
