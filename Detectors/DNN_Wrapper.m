%% Wrapper script to initialize workspace variables

clc; 
clear all;
close all;

% Unpack a json string from FCP 

%currentMode = 1; %placeholder for Active State


time = [1:25]';
modes = ones(size(time));

currentMode = [time, modes];