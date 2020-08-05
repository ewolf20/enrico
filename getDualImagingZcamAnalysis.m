function [struct_out] = getDualImagingZcamAnalysis(filepath)

ScanParmater = 0;

largeMBwidthX = 250;
largeMBwidthY = 100;

smallMBwidthX = 240;
smallMBwidthY = 80;

countingMBlargeX = 80;
countingMBlargeY = 80;
countingMBsmallX = 20;
countingMBsmallY = 8;

BECoffsetX = -654;
BECoffsetY = 14;

averageYCenterK  = 167-20;
averageYCenterNa = 178-20;

measNa = Measurement('Na','imageStartKeyword','dual','sortFilesBy','name',...
                'plotImage','original','NormType','Box','plotOD',false,...
                'verbose',false,'storeImages',false,'recenterMarqueeBox',false);
measNa.settings.avIntPerPixelThreshold    = 0.1;
measNa.settings.LineDensityPixelAveraging = 2; 

measK = Measurement('K','imageStartKeyword','dual','sortFilesBy','name',...
                'plotImage','original','NormType','Box','plotOD',false,...
                'verbose',false,'storeImages',false,'recenterMarqueeBox',false);
measK.settings.avIntPerPixelThreshold    = 0.1;
measK.settings.LineDensityPixelAveraging = 2; 

defaultNaBox = [21 93 largeMBwidthX largeMBwidthY ];
measNa.settings.marqueeBox  = defaultNaBox;
measNa.settings.normBox     = [95    96   159     8];
measK.settings.marqueeBox   = [727 81 smallMBwidthX smallMBwidthY ];  
measK.settings.normBox      = [722    78   208    10];
centerXall = 400;
TOF = 0.0;

im = [];

measNa.analysis.lineDensityNaMatrix     = [];
measNa.analysis.ODimageNaStack          = [];
measK.analysis.lineDensityKMatrix       = [];
measK.analysis.ODimageKStack            = []; 
measK.analysis.NcntSmall                = [];

OmegaX = 2*pi*12.2;
OmegaY = 2*pi*94;
OmegaZ = 2*pi*103;
tic
trueIdx = 0;
% load new images for K and Na
measNa.loadNewestSPEImage(ScanParmater,'FilePath',filepath);
measK.loadNewestSPEImage(ScanParmater,'FilePath',filepath);
%fit Na with large box
trueIdx = trueIdx+1;
measNa.fitIntegratedGaussian('last');
% set Na small MB and refit
centerX_Na = round(2*measNa.analysis.fitIntegratedGaussX.param(end,3)+measNa.settings.marqueeBox(1));
centerX_Na = max(centerX_Na,smallMBwidthX/2+2);
centerY_Na = round(2*measNa.analysis.fitIntegratedGaussY.param(end,3)+measNa.settings.marqueeBox(2));
if isnan(centerY_Na)
    centerY_Na = 93;
end
%make small MB for Na and do proper analysis
measNa.settings.marqueeBox=[centerX_Na-smallMBwidthX/2 centerY_Na-smallMBwidthY/2 smallMBwidthX smallMBwidthY ];
measNa.flushAllODImages();
measNa.createODimage('last');
measNa.createLineDensities();
measNa.fitBimodalExcludeCenter('last','BlackedOutODthreshold',4,'TFcut',1.2,'useLineDensity',false);
measNa.fitBimodalBose('last',OmegaY,OmegaX,'camPix',2.81e-6,'TFCut',.9,'BoseTFCut',1.2,'BlackedOutODThreshold',6,'TOF',TOF/1000,'useLineDensity',false);
measNa.fitIntegratedGaussian('last','useLineDensity',true);

%save some additional things
ODimageNa                                   = squeeze(measNa.images.ODImages(1,:,:));
measNa.analysis.ODimageNaStack(trueIdx,:,:) = ODimageNa;
lineDensityNa                               = measNa.lineDensities.Yintegrated(end,:);
measNa.analysis.lineDensityNaMatrix(end+1,:)= lineDensityNa;

%make K MB based on Na and analyze
centerX = centerX_Na-BECoffsetX;
centerY = centerY_Na-BECoffsetY;
measK.settings.marqueeBox=[centerX-smallMBwidthX/4 centerY-smallMBwidthY/32 smallMBwidthX/2 smallMBwidthY/16 ];
measK.flushAllODImages();
measK.createODimage('last');
measK.createLineDensities();
measK.fitIntegratedGaussian('last','useLineDensity',true,'fitY',false);

%save some additional things
ODimageK                                    = squeeze(measK.images.ODImages(1,:,:));
measK.analysis.ODimageKStack(trueIdx,:,:)   = ODimageK;
lineDensityK                                = measK.lineDensities.Yintegrated(end,:);
measK.analysis.lineDensityKMatrix(end+1,:)  = lineDensityK;


% K counting in small box
measK.settings.marqueeBox=[centerX-countingMBsmallX/2 ...
    centerY-countingMBsmallY/2 ...
    countingMBsmallX countingMBsmallY ];
measK.flushAllODImages();
measK.createODimage('last');
measK.plotODImage('last');
measK.bareNcntAverageMarqueeBox;
measK.analysis.NcntSmall(end+1) = measK.analysis.bareNcntAverageMarqueeBoxValues(end);


% set back to large MB
measNa.settings.marqueeBox=defaultNaBox;
measNa.flushAllODImages();
toc

struct_out.K_analysis = measK.analysis; 
struct_out.K_settings = measK.settings; 
struct_out.Na_analysis = measNa.analysis; 
struct_out.Na_settings = measNa.settings; 

end


