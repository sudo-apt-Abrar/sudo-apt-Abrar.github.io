import React from 'react'

const About = () => {
  return (
    <div name="about" className="w-full h-screen bg-gradient-to-b from-gray-800 to-black text-white">
        <div className="max-w-screen-lg p-4 mx-auto flex-col justify-center w-full h-full">
            <div className='pb-2'>
                <p className='text-4xl font-bold inline border-b-4 border-gray-500'>
                    About
                </p>
            </div>
            <p className='text-2xl mt-20'>
                
                Currently pursuing B.Tech in Computer Science from MIT, Manipal(19-23) 
                <br/>I am well-versed with domains related to Front-End Development and Artifical Intelligence.  
            </p>
            <br/>
            <p className='text-2xl'>
                If you'd like to hire me, enquire about me or give me feedback of any kind. I'll be delighted to hear from you.
                <br/> I hang out a lot on Twitter and will answer all your questions through a DM if that is more practical to you!
            </p>
        </div>
    </div>
  )
}

export default About