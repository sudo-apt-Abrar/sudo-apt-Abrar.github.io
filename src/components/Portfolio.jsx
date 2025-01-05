import React from 'react'
import img1 from '../assets/portfolio/img1.png';
import img2 from '../assets/portfolio/img2.jpg';
import img3 from '../assets/portfolio/img3.jpg';
// import img4 from '../assets/portfolio/img4.jpg';
import img5 from '../assets/portfolio/img5.jpg';
import img6 from '../assets/portfolio/img6.jpg';

const Portfolio = () => {

    const portfolios = [
        {
            id:1,
            src:img1,
            href:'https://github.com/sudo-apt-Abrar/Memories-React-Project',
            href2:'https://github.com/sudo-apt-Abrar/Memories-React-Project',
        },
        {
            id:2,
            src: img2,
            href:'https://huggingface.co/sudoabrar/DialoGPT-small-dwight',
            href2:'https://github.com/sudo-apt-Abrar/BearsandBeets',
        },
        {
            id:3,
            src: img3,
            href:'https://abrarsyed.in/A-Star-Visualizer/',
            href2:'https://github.com/sudo-apt-Abrar/A-Star-Visualizer',
        },
        {
            id:4,
            src: img6,
            href:'https://github.com/sudo-apt-Abrar/FootballAnalytics',
            href2:'https://github.com/sudo-apt-Abrar/FootballAnalytics',
        },
        {
            id:5,
            src: img5,
            href:'https://www.youtube.com/watch?v=OiCYOhngpHg',
            href2:'https://github.com/sudo-apt-Abrar/CarlaPathPlanning',
        },
        // {
        //     id:6,
        //     src: img4,
        //     href:'https://github.com/sudo-apt-Abrar/DocUploader',
        //     href2:'https://github.com/sudo-apt-Abrar/DocUploader',
        // },
    ]

  return (
    <div name="portfolio" className='bg-gradient-to-b from-black to-gray-800 w-full text-white md:h-screen'>
        
        <div className='max-w-screen-lg p-4 mx-auto flex flex-col justify-center w-full h-full'>
            <div>
                <p className='text-4xl font-bold inline border-b-4 border-gray-500 p-2'>Portfolio</p>
                <p className="py-6">Check out some of my work right here!</p>
            </div>

            
            <div className='grid sm:grid-cols-2 md:grid-cols-3 gap-8 px-12 sm:px-0'>
                {
                    portfolios.map(({id,src,href,href2}) => (
                        <div key={id} className='shadow-md shadow-gray-600 rounded-lg'>
                            <img src={src} alt="" className='rounded-md duration-200 hover:scale-105' />
                            <div className='flex items-center justify-center'>
                                <button className="w-1/2 px-6 py-3 m-4 duration-200 hover:scale-105"><a href={href}>Demo</a></button>
                                <button className="w-1/2 px-6 py-3 m-4 duration-200 hover:scale-105"><a href={href2}>Code</a></button>
                            </div>
                        </div>
                    ))
                }

                
            </div>

        </div>
    </div>
  )
}

export default Portfolio